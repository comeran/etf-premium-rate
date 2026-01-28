# -*- coding: UTF-8 -*-
"""
ETF/LOF溢价率报告生成器

功能：
    - 自动获取A股ETF和LOF基金的实时溢价率数据
    - 生成精美的HTML格式邮件报告
    - 支持定时自动发送

使用方法:
    python src/etf_premium_rate.py

配置文件:
    config.yaml - 邮件和报告配置（需要从 config.example.yaml 复制并填写）

依赖安装:
    pip install -r requirements.txt

说明:
    - 溢价率 = (场内价格 - 场外价格) / 场外价格 * 100%
    - 溢价率为正表示溢价，为负表示折价
"""

import pandas as pd
import akshare as ak
import time
from datetime import datetime, timezone, timedelta
import sys
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import os
from functools import wraps
import socket

# 设置全局socket超时时间（30秒），避免请求长时间挂起
# 注意：这会影响整个Python进程中的所有socket连接
# 如果此模块被导入到其他应用中，需要注意这个全局设置的影响
socket.setdefaulttimeout(30)

def safe_truncate(text, max_length=100):
    """
    安全截断字符串
    
    Args:
        text: 要截断的字符串
        max_length: 最大字符长度
    
    Returns:
        截断后的字符串，如果被截断则添加"..."后缀
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def retry_on_failure(max_retries=2, delay=2, backoff=2, exceptions=(Exception,)):
    """
    装饰器：在函数失败时自动重试
    
    Args:
        max_retries: 最大重试次数（默认2次，加上初始尝试共3次）
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的倍数增长因子
        exceptions: 需要捕获并重试的异常类型元组
    """
    if max_retries < 0:
        max_retries = 0
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        error_msg = safe_truncate(str(e), 100)
                        print(f"  尝试 {attempt + 1}/{max_retries + 1} 失败: {error_msg}")
                        print(f"  等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"  所有 {max_retries + 1} 次尝试均失败")
            
            # 如果所有重试都失败，抛出最后一个异常
            if last_exception:
                raise last_exception
            # 理论上不应该到这里，但以防万一
            raise Exception("重试失败但没有捕获到异常")
        
        return wrapper
    return decorator

def get_etf_list():
    """获取ETF基金列表"""
    print("正在获取ETF基金列表...")
    try:
        # 获取ETF基金列表
        etf_list = ak.fund_etf_hist_sina()
        return etf_list
    except Exception as e:
        print(f"获取ETF列表失败: {e}")
        # 备用方案：使用基金基本信息
        try:
            etf_list = ak.fund_etf_category_sina(symbol="ETF基金")
            return etf_list
        except Exception as e2:
            print(f"备用方案也失败: {e2}")
            return None

@retry_on_failure(max_retries=2, delay=3, backoff=2)
def get_etf_realtime_data():
    """获取ETF实时行情数据（场内价格）
    
    注意：此函数会尝试从东方财富获取数据，失败时会抛出异常
    """
    print("正在获取ETF实时行情数据...")
    
    # 获取ETF实时行情
    try:
        df = ak.fund_etf_spot_em()
        if df is not None and not df.empty:
            print(f"✓ 成功获取 {len(df)} 条ETF数据")
            return df
        else:
            raise Exception("ETF数据为空")
    except Exception as e:
        error_msg = safe_truncate(str(e), 150)
        print(f"  ETF获取失败: {error_msg}")
        raise

@retry_on_failure(max_retries=2, delay=3, backoff=2)
def get_lof_realtime_data():
    """获取LOF基金实时行情数据（场内价格）
    
    注意：此函数会尝试从东方财富获取数据，失败时会抛出异常
    """
    print("正在获取LOF基金实时行情数据...")
    try:
        df = ak.fund_lof_spot_em()
        if df is not None and not df.empty:
            print(f"✓ 成功获取 {len(df)} 条LOF数据")
            return df
        else:
            raise Exception("LOF数据为空")
    except Exception as e:
        error_msg = safe_truncate(str(e), 150)
        print(f"  LOF获取失败: {error_msg}")
        raise

def get_etf_nav_data():
    """获取ETF净值数据（场外价格）"""
    print("正在获取ETF净值数据...")
    try:
        # 方法1: 获取ETF基金净值
        df = ak.fund_etf_fund_info_em()
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"方法1获取净值数据失败: {e}")
    
    try:
        # 方法2: 备用方案
        df = ak.fund_open_fund_info_em(fund="159919", indicator="单位净值走势")
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"方法2获取净值数据失败: {e}")
    
    return None

def calculate_premium_rate(spot_price, nav_price):
    """计算溢价率"""
    if pd.isna(spot_price) or pd.isna(nav_price) or nav_price == 0:
        return None
    premium_rate = (spot_price - nav_price) / nav_price * 100
    return round(premium_rate, 4)

# 全局变量：缓存所有基金的净值数据
_all_fund_nav_cache = None

def get_all_fund_nav():
    """获取所有基金的净值数据（缓存）"""
    global _all_fund_nav_cache
    if _all_fund_nav_cache is None:
        try:
            print("正在获取所有基金的净值数据...")
            _all_fund_nav_cache = ak.fund_open_fund_daily_em()
            if _all_fund_nav_cache is not None and not _all_fund_nav_cache.empty:
                print(f"成功获取 {len(_all_fund_nav_cache)} 条基金净值数据")
        except Exception as e:
            print(f"获取基金净值数据失败: {e}")
            _all_fund_nav_cache = pd.DataFrame()
    return _all_fund_nav_cache

def get_fund_nav_by_code(code):
    """根据基金代码获取净值（场外价格）- 用于LOF基金"""
    try:
        # 获取所有基金净值数据
        all_nav_data = get_all_fund_nav()
        if all_nav_data is None or all_nav_data.empty:
            return None
        
        # 在净值数据中查找对应代码的基金
        if '基金代码' in all_nav_data.columns:
            fund_nav = all_nav_data[all_nav_data['基金代码'] == code]
            if len(fund_nav) > 0:
                # 获取基金记录
                fund_record = fund_nav.iloc[0]
                
                # 查找最新的单位净值列（格式为：日期-单位净值）
                nav_cols = [col for col in fund_record.index if '单位净值' in col and not col.startswith('日')]
                if nav_cols:
                    # 按日期排序，获取最新的有效值
                    nav_cols_sorted = sorted(nav_cols, reverse=True)
                    for nav_col in nav_cols_sorted:
                        nav = fund_record[nav_col]
                        # 处理空字符串和NaN
                        if pd.isna(nav) or nav == '' or nav == ' ':
                            continue
                        try:
                            nav_float = float(nav)
                            if nav_float > 0:
                                return nav_float
                        except (ValueError, TypeError):
                            continue
                
                # 如果没有找到单位净值，尝试累计净值
                nav_cols = [col for col in fund_record.index if '累计净值' in col and not col.startswith('日')]
                if nav_cols:
                    nav_cols_sorted = sorted(nav_cols, reverse=True)
                    for nav_col in nav_cols_sorted:
                        nav = fund_record[nav_col]
                        if pd.isna(nav) or nav == '' or nav == ' ':
                            continue
                        try:
                            nav_float = float(nav)
                            if nav_float > 0:
                                return nav_float
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        pass
    return None

def get_etf_data():
    """获取并合并ETF和LOF基金数据"""
    print("=" * 60)
    print("开始获取ETF和LOF基金数据...")
    print("=" * 60)
    
    # 获取ETF实时行情（场内价格）
    try:
        etf_df = get_etf_realtime_data()
        if etf_df is not None and not etf_df.empty:
            print(f"✅ 获取到 {len(etf_df)} 条ETF实时行情数据")
            etf_df['基金类型'] = 'ETF'
        else:
            etf_df = pd.DataFrame()
            print("⚠️ ETF实时行情数据为空")
    except Exception as e:
        etf_df = pd.DataFrame()
        error_msg = safe_truncate(str(e), 100)
        print(f"⚠️ 无法获取ETF实时行情数据: {error_msg}")
    
    # 获取LOF基金实时行情（场内价格）
    try:
        lof_df = get_lof_realtime_data()
        if lof_df is not None and not lof_df.empty:
            print(f"✅ 获取到 {len(lof_df)} 条LOF基金实时行情数据")
            lof_df['基金类型'] = 'LOF'
        else:
            lof_df = pd.DataFrame()
            print("⚠️ LOF基金实时行情数据为空")
    except Exception as e:
        lof_df = pd.DataFrame()
        error_msg = safe_truncate(str(e), 100)
        print(f"⚠️ 无法获取LOF基金实时行情数据: {error_msg}")
    
    # 合并ETF和LOF数据
    if etf_df.empty and lof_df.empty:
        print("\n" + "=" * 60)
        print("❌ 错误：无法获取任何基金数据")
        print("=" * 60)
        print("\n可能的原因：")
        print("1. 网络连接问题 - 请检查网络连接")
        print("2. API服务暂时不可用 - 请稍后重试")
        print("3. DNS解析失败 - 请检查DNS设置")
        print("4. 防火墙或代理阻止了请求")
        print("\n建议：")
        print("- 稍后再试（等待几分钟后重新运行）")
        print("- 检查是否能访问 push2.eastmoney.com")
        print("- 检查是否能访问 finance.sina.com.cn")
        print("=" * 60 + "\n")
        return None
    
    if not etf_df.empty and not lof_df.empty:
        spot_df = pd.concat([etf_df, lof_df], ignore_index=True)
    elif not etf_df.empty:
        spot_df = etf_df
    else:
        spot_df = lof_df
    
    print(f"总共获取到 {len(spot_df)} 条基金实时行情数据")
    print(f"数据列: {list(spot_df.columns)}")
    
    # 检查实时行情数据中是否已有IOPV实时估值（场外价格）
    has_iopv = 'IOPV实时估值' in spot_df.columns
    if has_iopv:
        print("实时行情数据中包含IOPV实时估值，直接使用作为场外价格")
        nav_df = None  # 不需要单独获取净值数据
    else:
        # 获取净值数据（场外价格）
        nav_df = get_etf_nav_data()
        if nav_df is None or nav_df.empty:
            print("无法获取净值数据，将尝试逐个获取基金净值...")
            nav_df = None
        else:
            print(f"获取到 {len(nav_df)} 条净值数据")
    
    # 数据清洗和合并
    result_list = []
    skipped_stats = {
        'no_code_or_name': 0,
        'no_spot_price': 0,
        'no_nav_price': 0,
        'premium_calc_failed': 0,
        'other_errors': 0
    }
    
    # 预先获取净值数据缓存（包含申购赎回状态和手续费信息）
    print("正在获取基金净值及申购赎回信息...")
    get_all_fund_nav()  # 预加载净值数据
    
    print(f"开始处理 {len(spot_df)} 条实时行情数据...")
    # 处理实时行情数据
    for idx, row in spot_df.iterrows():
        try:
            # 获取代码和名称
            code = None
            name = None
            
            # 尝试不同的列名
            for col in ['代码', '基金代码', 'code', 'symbol']:
                if col in row.index:
                    code = str(row[col]).strip()
                    break
            
            for col in ['名称', '基金名称', 'name', '基金简称']:
                if col in row.index:
                    name = str(row[col]).strip()
                    break
            
            if not code or not name:
                skipped_stats['no_code_or_name'] += 1
                continue
            
            # 获取场内价格
            spot_price = None
            for col in ['最新价', '现价', '当前价', 'price', '最新净值']:
                if col in row.index:
                    spot_price = row[col]
                    if not pd.isna(spot_price):
                        break
            
            if pd.isna(spot_price) or spot_price is None or spot_price == 0:
                skipped_stats['no_spot_price'] += 1
                continue
            
            # 获取交易量（成交量）
            volume = None
            for col in ['成交量', '成交额', '成交金额', '量', 'volume', '总手', '成交手数', '成交数量']:
                if col in row.index:
                    volume_value = row[col]
                    if not pd.isna(volume_value) and volume_value is not None:
                        try:
                            volume = float(volume_value)
                            if volume > 0:
                                break
                        except (ValueError, TypeError):
                            continue
            
            # 查找对应的净值（场外价格）
            nav_price = None
            
            # 方法1: 优先从实时行情中获取IOPV实时估值（这是场外价格/净值）
            for col in ['IOPV实时估值', 'IOPV', '参考净值', '净值', '单位净值']:
                if col in row.index:
                    nav_price = row[col]
                    if not pd.isna(nav_price) and nav_price != 0:
                        break
            
            # 方法2: 如果实时行情中没有，从净值数据中查找
            if (pd.isna(nav_price) or nav_price is None or nav_price == 0) and nav_df is not None and '代码' in nav_df.columns:
                nav_row = nav_df[nav_df['代码'] == code]
                if not nav_row.empty:
                    for nav_col in ['净值', '单位净值', '累计净值', 'nav']:
                        if nav_col in nav_row.columns:
                            nav_price = nav_row.iloc[0][nav_col]
                            if not pd.isna(nav_price) and nav_price != 0:
                                break
            
            # 方法3: 如果前两种方法都没有找到，且是LOF基金，尝试通过API获取单个基金的净值
            if (pd.isna(nav_price) or nav_price is None or nav_price == 0):
                fund_type = row.get('基金类型', 'ETF')
                if fund_type == 'LOF':
                    nav_price = get_fund_nav_by_code(code)
                    if nav_price is not None and nav_price > 0:
                        time.sleep(0.1)  # 避免API调用过快
            
            if pd.isna(nav_price) or nav_price is None or nav_price == 0:
                skipped_stats['no_nav_price'] += 1
                continue
            
            # 计算溢价率
            premium_rate = calculate_premium_rate(spot_price, nav_price)
            if premium_rate is None:
                skipped_stats['premium_calc_failed'] += 1
                continue
            
            # 获取基金类型
            fund_type = row.get('基金类型', 'ETF')
            
            # 获取申购状态、赎回状态和手续费
            purchase_status = ''
            redeem_status = ''
            fee_rate = ''
            purchase_limit = ''
            
            # 从净值数据中获取这些信息
            all_nav_data = get_all_fund_nav()
            if all_nav_data is not None and not all_nav_data.empty and '基金代码' in all_nav_data.columns:
                fund_nav_info = all_nav_data[all_nav_data['基金代码'] == code]
                if len(fund_nav_info) > 0:
                    fund_info = fund_nav_info.iloc[0]
                    if '申购状态' in fund_info.index:
                        purchase_status = str(fund_info['申购状态']).strip()
                    if '赎回状态' in fund_info.index:
                        redeem_status = str(fund_info['赎回状态']).strip()
                    if '手续费' in fund_info.index:
                        fee_rate = str(fund_info['手续费']).strip()
            
            # 尝试从其他API获取限购金额（如果申购状态是"限大额"但没有具体金额）
            purchase_limit_amount = ''
            if purchase_status and ('限大额' in purchase_status or '限额' in purchase_status):
                try:
                    # 尝试从基金详细信息中获取限购金额
                    fund_list = ak.fund_name_em()
                    fund_name_info = fund_list[fund_list['基金代码'] == code]
                    if len(fund_name_info) > 0:
                        fund_name = fund_name_info.iloc[0]['基金简称']
                        # 尝试获取基金申购赎回详细信息
                        try:
                            # 注意：这里可能需要根据akshare的实际API调整
                            # 某些API可能包含限购金额信息
                            pass
                        except:
                            pass
                except:
                    pass
            
            # 处理申购限额（从申购状态中提取，并尝试获取限购金额）
            purchase_limit_amount = ''
            if fund_type == 'ETF':
                # ETF主要在场内交易，申购赎回信息可能不完整
                if purchase_status and purchase_status != '' and purchase_status != 'nan':
                    if '限大额' in purchase_status or '限额' in purchase_status:
                        purchase_limit = '限大额'
                        # 尝试从申购状态中提取金额（如果有的话）
                        import re
                        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*[万千]?元', purchase_status)
                        if amount_match:
                            purchase_limit_amount = amount_match.group(1)
                    elif '暂停申购' in purchase_status:
                        purchase_limit = '暂停'
                    elif '开放申购' in purchase_status:
                        purchase_limit = '开放'
                    else:
                        purchase_limit = purchase_status
                else:
                    purchase_limit = '场内交易'
                
                if not redeem_status or redeem_status == '' or redeem_status == 'nan':
                    redeem_status = '场内交易'
            else:
                # LOF基金
                if '限大额' in purchase_status or '限额' in purchase_status:
                    purchase_limit = '限大额'
                    # 尝试从申购状态中提取金额
                    import re
                    # 匹配各种金额格式：1000元、100万元、1000万等
                    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*([万千]?)元?', purchase_status)
                    if amount_match:
                        amount = float(amount_match.group(1))
                        unit = amount_match.group(2)
                        if unit == '万':
                            purchase_limit_amount = f"{amount:.0f}万"
                        elif unit == '千':
                            purchase_limit_amount = f"{amount:.0f}千"
                        else:
                            purchase_limit_amount = f"{amount:.0f}元"
                elif '暂停申购' in purchase_status:
                    purchase_limit = '暂停'
                elif '开放申购' in purchase_status or purchase_status == '':
                    purchase_limit = '开放'
                else:
                    purchase_limit = purchase_status if purchase_status else '未知'
                
                if not redeem_status or redeem_status == '' or redeem_status == 'nan':
                    redeem_status = '未知'
            
            # 如果有限购金额，合并到申购状态中
            if purchase_limit_amount:
                purchase_limit = f"{purchase_limit}({purchase_limit_amount})"
            elif purchase_limit == '限大额':
                # 如果显示"限大额"但没有具体金额，保持原样
                # 注：由于数据源限制，可能无法获取具体限购金额
                purchase_limit = '限大额'
            
            result_list.append({
                '基金名称': name,
                '代码': code,
                '基金类型': fund_type,
                '场内价格': round(float(spot_price), 4),
                '场外价格': round(float(nav_price), 4),
                '溢价率': premium_rate,
                '交易量': volume if volume is not None and volume > 0 else 0,
                '申购状态': purchase_limit,
                '赎回状态': redeem_status if redeem_status else '未知',
                '手续费': fee_rate if fee_rate else '未知'
            })
            
        except Exception as e:
            # 静默跳过错误数据
            skipped_stats['other_errors'] += 1
            continue
    
    # 打印处理统计信息
    print(f"\n数据处理统计:")
    print(f"  成功处理: {len(result_list)} 条")
    print(f"  跳过原因:")
    print(f"    - 缺少代码或名称: {skipped_stats['no_code_or_name']} 条")
    print(f"    - 缺少场内价格: {skipped_stats['no_spot_price']} 条")
    print(f"    - 缺少场外价格(净值): {skipped_stats['no_nav_price']} 条")
    print(f"    - 溢价率计算失败: {skipped_stats['premium_calc_failed']} 条")
    print(f"    - 其他错误: {skipped_stats['other_errors']} 条")
    
    if not result_list:
        print("\n❌ 未能获取到有效数据")
        print("   所有记录都被过滤掉了，请检查数据源和列名是否匹配")
        return None
    
    result_df = pd.DataFrame(result_list)
    print(f"\n✅ 成功处理 {len(result_df)} 条有效ETF数据")
    return result_df

def load_config():
    """加载配置文件
    优先从环境变量（Repository secrets）读取，其次从 config.yaml 读取
    """
    config = {}
    
    # 优先从环境变量读取配置（GitHub Actions Repository secrets）
    print("正在从环境变量读取配置...")
    email_config = {}
    smtp_config = {}
    
    # 读取所有环境变量
    recipients_env = os.getenv('EMAIL_RECIPIENTS', '')
    email_subject_env = os.getenv('EMAIL_SUBJECT', '')
    
    # 读取 SMTP 配置
    if os.getenv('EMAIL_SMTP_HOST'):
        smtp_config['host'] = os.getenv('EMAIL_SMTP_HOST')
    if os.getenv('EMAIL_SMTP_PORT'):
        try:
            smtp_config['port'] = int(os.getenv('EMAIL_SMTP_PORT'))
        except (ValueError, TypeError):
            pass
    if os.getenv('EMAIL_SMTP_USE_TLS'):
        smtp_config['use_tls'] = os.getenv('EMAIL_SMTP_USE_TLS').lower() != 'false'
    if os.getenv('EMAIL_USERNAME'):
        smtp_config['username'] = os.getenv('EMAIL_USERNAME')
    if os.getenv('EMAIL_PASSWORD'):
        smtp_config['password'] = os.getenv('EMAIL_PASSWORD')
    
    # 读取收件人列表（支持逗号分隔的多个邮箱）
    if recipients_env:
        # 处理逗号分隔的邮箱列表
        recipients = [email.strip() for email in recipients_env.split(',') if email.strip()]
        if recipients:
            email_config['recipients'] = recipients
    
    # 读取邮件主题
    if email_subject_env:
        email_config['subject'] = email_subject_env
    
    # 如果从环境变量读取到了完整配置，使用环境变量配置
    if smtp_config and email_config.get('recipients'):
        config['email'] = {
            'smtp': smtp_config,
            **email_config
        }
        print("✅ 已从环境变量加载配置")
    else:
        # 从 config.yaml 读取配置
        print("环境变量配置不完整，尝试从 config.yaml 读取...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # src 的父目录就是项目根目录
    
    # 优先从项目根目录查找配置文件
    config_paths = [
        os.path.join(project_root, 'config.yaml'),  # 项目根目录
        'config.yaml',  # 当前工作目录（兼容性）
    ]
    
    config_path = None
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if config_path is None:
        print(f"错误: 配置文件 config.yaml 不存在")
        print(f"请复制 {os.path.join(project_root, 'config.example.yaml')} 为 config.yaml 并填写配置")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    config = file_config
                    print(f"✅ 已从配置文件加载: {config_path}")
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return None
    
    # 合并环境变量和配置文件（环境变量优先级更高）
    if smtp_config:
        if 'email' not in config:
            config['email'] = {}
        if 'smtp' not in config['email']:
            config['email']['smtp'] = {}
        # 环境变量覆盖配置文件
        config['email']['smtp'].update(smtp_config)
    
    if recipients_env:
        recipients = [email.strip() for email in recipients_env.split(',') if email.strip()]
        if recipients:
            if 'email' not in config:
                config['email'] = {}
            config['email']['recipients'] = recipients
    
    if email_subject_env:
        if 'email' not in config:
            config['email'] = {}
        config['email']['subject'] = email_subject_env
    
    # 读取报告配置（环境变量优先）
    report_top_n_env = os.getenv('REPORT_TOP_N')
    if report_top_n_env:
        try:
            if 'report' not in config:
                config['report'] = {}
            config['report']['top_n'] = int(report_top_n_env)
            print(f"📊 配置读取: REPORT_TOP_N 从环境变量读取: {config['report']['top_n']}")
        except (ValueError, TypeError):
            pass
    elif 'report' in config and 'top_n' in config['report']:
        print(f"📊 配置读取: top_n 从 config.yaml 读取: {config['report']['top_n']}")
    
    report_only_premium_env = os.getenv('REPORT_ONLY_PREMIUM')
    if report_only_premium_env:
        if 'report' not in config:
            config['report'] = {}
        config['report']['only_premium'] = report_only_premium_env.lower() == 'true'
        print(f"📊 配置读取: REPORT_ONLY_PREMIUM 从环境变量读取: {config['report']['only_premium']}")
    elif 'report' in config and 'only_premium' in config['report']:
        print(f"📊 配置读取: only_premium 从 config.yaml 读取: {config['report']['only_premium']}")
    
    
    # 清理和验证 recipients 列表（过滤掉 None 和空值）
    if 'email' in config and 'recipients' in config['email']:
        recipients = config['email']['recipients']
        if recipients:
            print(f"📧 配置读取: 原始收件人列表: {recipients}")
            # 过滤掉 None、空字符串和非字符串类型
            cleaned_recipients = [
                r.strip() for r in recipients 
                if r is not None and isinstance(r, str) and r.strip()
            ]
            if cleaned_recipients:
                config['email']['recipients'] = cleaned_recipients
                print(f"📧 配置读取: 清理后的收件人列表: {cleaned_recipients}")
            else:
                # 如果清理后为空，删除 recipients，让代码后续报错
                print("⚠️  警告: 收件人列表清理后为空")
                # 检查是否是从环境变量读取的（环境变量不存在）
                if not recipients_env:
                    print("   提示: EMAIL_RECIPIENTS 环境变量未配置，且 config.yaml 中收件人列表为空")
                    print("   请配置 GitHub Secrets 中的 EMAIL_RECIPIENTS 或在 config.yaml 中设置收件人")
                config['email']['recipients'] = []
        else:
            # recipients 是空列表或 None
            if isinstance(recipients, list) and len(recipients) == 0:
                print("⚠️  警告: 配置中 recipients 为空列表")
                if not recipients_env:
                    print("   提示: EMAIL_RECIPIENTS 环境变量未配置，且 config.yaml 中收件人列表为空")
                    print("   请配置 GitHub Secrets 中的 EMAIL_RECIPIENTS 或在 config.yaml 中设置收件人")
            else:
                print("⚠️  警告: 配置中 recipients 不存在或为 None")
    
    return config

def generate_email_html(df, top_n=100, only_premium=False):
    """生成HTML格式的邮件内容（针对邮箱优化）"""
    if df is None or df.empty:
        return "<html><body><p>未能获取到数据</p></body></html>"
    
    # 按溢价率排序
    df_sorted = df.sort_values('溢价率', ascending=False)
    # 使用东八区时间（北京时间）
    beijing_tz = timezone(timedelta(hours=8))
    timestamp = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    # 计算统计数据
    total_count = len(df)
    etf_count = len(df[df['基金类型'] == 'ETF']) if '基金类型' in df.columns else 0
    lof_count = len(df[df['基金类型'] == 'LOF']) if '基金类型' in df.columns else 0
    avg_premium = df['溢价率'].mean()
    max_premium = df['溢价率'].max()
    min_premium = df['溢价率'].min()
    premium_count = len(df[df['溢价率'] > 0])
    discount_count = len(df[df['溢价率'] < 0])
    
    # 生成HTML邮件
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        .stats {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-label {{
            font-size: 12px;
            opacity: 0.9;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f0f7ff;
        }}
        .premium-positive {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .premium-negative {{
            color: #27ae60;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
            font-size: 12px;
        }}
        .section-title {{
            background-color: #34495e;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            margin: 30px 0 15px 0;
            font-size: 18px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 ETF/LOF溢价率排行榜</h1>
        
        <div style="text-align: center; color: #7f8c8d; margin-bottom: 20px;">
            <p>📅 更新时间: <strong>{timestamp}</strong></p>
            <p>📊 数据来源: akshare</p>
        </div>
        
        <div class="stats">
            <h2 style="margin-top: 0; text-align: center;">📈 统计概览</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">总基金数量</div>
                    <div class="stat-value">{total_count}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">ETF数量</div>
                    <div class="stat-value">{etf_count}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">LOF数量</div>
                    <div class="stat-value">{lof_count}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">平均溢价率</div>
                    <div class="stat-value">{avg_premium:.2f}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">最高溢价率</div>
                    <div class="stat-value">{max_premium:.2f}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">最低溢价率</div>
                    <div class="stat-value">{min_premium:.2f}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">溢价基金数量</div>
                    <div class="stat-value">{premium_count}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">折价基金数量</div>
                    <div class="stat-value">{discount_count}</div>
                </div>
            </div>
        </div>
        
        <div class="section-title">🔺 溢价率最高 Top {top_n}</div>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>基金名称</th>
                    <th>代码</th>
                    <th>类型</th>
                    <th>场内价</th>
                    <th>场外价</th>
                    <th>溢价率</th>
                    <th>交易量</th>
                    <th>申购状态</th>
                    <th>赎回状态</th>
                    <th>手续费</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # 生成溢价率最高的表格
    top_high = df_sorted.head(top_n)
    for idx, (_, row) in enumerate(top_high.iterrows(), 1):
        fund_name = row.get('基金名称', row.get('ETF名称', ''))
        fund_type = row.get('基金类型', 'ETF')
        purchase_status = row.get('申购状态', '未知')
        redeem_status = row.get('赎回状态', '未知')
        fee_rate = row.get('手续费', '未知')
        
        premium_rate = row['溢价率']
        premium_class = 'premium-positive' if premium_rate > 0 else 'premium-negative'
        premium_str = f"{premium_rate:.2f}%"
        if premium_rate > 0:
            premium_str = f"🔺 {premium_str}"
        elif premium_rate < 0:
            premium_str = f"🔻 {premium_str}"
        
        # 格式化交易量显示
        volume_value = row.get('交易量', 0)
        if volume_value and volume_value > 0:
            if volume_value >= 100000000:
                volume_str = f"{volume_value/100000000:.2f}亿"
            elif volume_value >= 10000:
                volume_str = f"{volume_value/10000:.2f}万"
            else:
                volume_str = f"{volume_value:.0f}"
        else:
            volume_str = "-"
        
        html += f"""                <tr>
                    <td>{idx}</td>
                    <td>{fund_name}</td>
                    <td>{row['代码']}</td>
                    <td>{fund_type}</td>
                    <td>{row['场内价格']:.4f}</td>
                    <td>{row['场外价格']:.4f}</td>
                    <td class="{premium_class}">{premium_str}</td>
                    <td>{volume_str}</td>
                    <td>{purchase_status}</td>
                    <td>{redeem_status}</td>
                    <td>{fee_rate}</td>
                </tr>
"""
    
    html += """            </tbody>
        </table>
"""
    
    # 如果不只显示溢价，也显示折价最高的
    if not only_premium:
        html += f"""        
        <div class="section-title">🔻 溢价率最低 Top {top_n} (折价最高)</div>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>基金名称</th>
                    <th>代码</th>
                    <th>类型</th>
                    <th>场内价</th>
                    <th>场外价</th>
                    <th>溢价率</th>
                    <th>交易量</th>
                    <th>申购状态</th>
                    <th>赎回状态</th>
                    <th>手续费</th>
                </tr>
            </thead>
            <tbody>
"""
        
        top_low = df_sorted.tail(top_n).sort_values('溢价率', ascending=True)
        for idx, (_, row) in enumerate(top_low.iterrows(), 1):
            fund_name = row.get('基金名称', row.get('ETF名称', ''))
            fund_type = row.get('基金类型', 'ETF')
            purchase_status = row.get('申购状态', '未知')
            redeem_status = row.get('赎回状态', '未知')
            fee_rate = row.get('手续费', '未知')
            
            premium_rate = row['溢价率']
            premium_class = 'premium-positive' if premium_rate > 0 else 'premium-negative'
            premium_str = f"{premium_rate:.2f}%"
            if premium_rate > 0:
                premium_str = f"🔺 {premium_str}"
            elif premium_rate < 0:
                premium_str = f"🔻 {premium_str}"
            
            # 格式化交易量显示
            volume_value = row.get('交易量', 0)
            if volume_value and volume_value > 0:
                if volume_value >= 100000000:
                    volume_str = f"{volume_value/100000000:.2f}亿"
                elif volume_value >= 10000:
                    volume_str = f"{volume_value/10000:.2f}万"
                else:
                    volume_str = f"{volume_value:.0f}"
            else:
                volume_str = "-"
            
            html += f"""                <tr>
                    <td>{idx}</td>
                    <td>{fund_name}</td>
                    <td>{row['代码']}</td>
                    <td>{fund_type}</td>
                    <td>{row['场内价格']:.4f}</td>
                    <td>{row['场外价格']:.4f}</td>
                    <td class="{premium_class}">{premium_str}</td>
                    <td>{volume_str}</td>
                    <td>{purchase_status}</td>
                    <td>{redeem_status}</td>
                    <td>{fee_rate}</td>
                </tr>
"""
        
        html += """            </tbody>
        </table>
"""
    
    html += """        
        <div class="footer">
            <p><strong>📝 说明</strong></p>
            <p>• 溢价率 = (场内价格 - 场外价格) / 场外价格 × 100%</p>
            <p>• 溢价率为正表示溢价，为负表示折价</p>
            <p>• 🔺 表示溢价，🔻 表示折价</p>
            <p>• 数据仅供参考，投资有风险，入市需谨慎</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

def send_email(config, html_content, subject):
    """发送邮件"""
    try:
        smtp_config = config.get('email', {}).get('smtp', {})
        recipients = config.get('email', {}).get('recipients', [])
        
        # 调试信息：打印原始 recipients
        print(f"📧 调试信息: 原始收件人列表: {recipients}")
        print(f"📧 调试信息: 收件人列表类型: {type(recipients)}")
        if recipients:
            print(f"📧 调试信息: 收件人数量: {len(recipients)}")
            for i, r in enumerate(recipients):
                print(f"📧 调试信息: 收件人[{i}]: {repr(r)} (类型: {type(r)})")
        
        # 验证收件人列表
        if not recipients:
            print("❌ 错误: 收件人列表为空，请检查配置")
            print("   请确保在环境变量 EMAIL_RECIPIENTS 或 config.yaml 中配置了收件人")
            return False
        
        # 过滤掉 None 和空字符串
        recipients = [r for r in recipients if r is not None and isinstance(r, str) and r.strip()]
        
        print(f"📧 调试信息: 清理后的收件人列表: {recipients}")
        
        if not recipients:
            print("❌ 错误: 收件人列表无效（全部为空或None），请检查配置")
            print("   请检查 config.yaml 中的 recipients 配置，确保所有邮箱地址都是有效的字符串")
            return False
        
        # 验证必需的 SMTP 配置
        required_fields = ['host', 'port', 'username', 'password']
        missing_fields = [field for field in required_fields if not smtp_config.get(field)]
        if missing_fields:
            print(f"❌ 错误: SMTP 配置缺少必需字段: {', '.join(missing_fields)}")
            return False
        
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_config['username']
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加HTML内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 连接SMTP服务器并发送
        if smtp_config.get('use_tls', True):
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'])
        
        server.login(smtp_config['username'], smtp_config['password'])
        server.sendmail(smtp_config['username'], recipients, msg.as_string())
        server.quit()
        
        print(f"✅ 邮件已成功发送到 {len(recipients)} 个收件人")
        for recipient in recipients:
            print(f"   - {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ 发送邮件失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    try:
        # 加载配置
        config = load_config()
        if config is None:
            return
        
        print("=" * 60)
        print("开始获取ETF/LOF溢价率数据...")
        print("=" * 60)
        
        # 获取数据
        df = get_etf_data()
        
        if df is None or df.empty:
            print("\n❌ 未能获取到有效的ETF/LOF数据")
            print("   请检查上述错误信息以了解详细原因")
            return
        
        print(f"✅ 成功获取 {len(df)} 条基金数据（包含ETF和LOF）")
        
        # 从配置中获取参数
        top_n = config.get('report', {}).get('top_n', 100)
        only_premium = config.get('report', {}).get('only_premium', False)
        
        # 生成HTML邮件内容
        print(f"\n正在生成邮件内容（Top {top_n}）...")
        html_content = generate_email_html(df, top_n=top_n, only_premium=only_premium)
        
        # 生成邮件主题（使用东八区时间）
        beijing_tz = timezone(timedelta(hours=8))
        date_str = datetime.now(beijing_tz).strftime("%Y-%m-%d")
        subject_template = config.get('email', {}).get('subject', '📊 ETF/LOF溢价率排行榜 - {date}')
        subject = subject_template.format(date=date_str)
        
        # 发送邮件
        print("\n正在发送邮件...")
        send_email(config, html_content, subject)
        
        print("\n" + "=" * 60)
        print("✅ 任务完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

