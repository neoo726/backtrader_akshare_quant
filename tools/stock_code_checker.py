#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票代码检查工具
用于检查股票/ETF代码的有效性，并获取基本信息
"""

import sys
import os
import akshare as ak
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from strategies.etf_rotation_strategy_v2 import ETF_POOL
except ImportError:
    logger.error("无法导入ETF_POOL，请确保文件存在")
    ETF_POOL = []

def check_stock_data_availability(stock_code, days=5):
    """
    
    
    Args:
        stock_code (str): ETF代码
        days (int): 检查最近几天的数据
        
    Returns:
        tuple: (是否可用, 数据详情)
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 使用ETF专用接口获取数据
        df = ak.fund_etf_hist_em(
            symbol=stock_code,
            period="daily",
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d'),
            adjust="qfq"
        )
        
        if df is None or df.empty:
            return False, "无法获取数据"
            
        return True, {
            "数据行数": len(df),
            "最新交易日": df['日期'].max() if '日期' in df.columns else df['trade_date'].max(),
            "最新收盘价": df['收盘'].iloc[-1] if '收盘' in df.columns else df['close'].iloc[-1],
            "最新成交量": df['成交量'].iloc[-1] if '成交量' in df.columns else df['volume'].iloc[-1]
        }
        
    except Exception as e:
        # 如果ETF接口失败，尝试使用fund_etf_spot_em获取当前数据
        try:
            etf_spot = ak.fund_etf_spot_em()
            etf_data = etf_spot[etf_spot['代码'] == stock_code]
            if not etf_data.empty:
                return True, {
                    "数据行数": 1,
                    "最新交易日": datetime.now().strftime('%Y-%m-%d'),
                    "最新收盘价": etf_data['最新价'].iloc[0],
                    "最新成交量": etf_data['成交量'].iloc[0]
                }
        except:
            pass
            
        return False, f"获取数据出错: {str(e)}"

def get_etf_info(stock_code):
    """
    获取ETF基本信息
    
    Args:
        stock_code (str): ETF代码
        
    Returns:
        dict: ETF信息
    """
    try:
        # 使用 fund_etf_spot_em 获取ETF实时行情
        etf_spot = ak.fund_etf_spot_em()
        
        # 查找对应的ETF
        etf_data = etf_spot[etf_spot['代码'] == stock_code]
        
        if etf_data.empty:
            # 尝试使用 fund_etf_fund_info_em 获取ETF基本信息
            etf_info = ak.fund_etf_fund_info_em(fund=stock_code)
            if etf_info is not None and not etf_info.empty:
                return etf_info.iloc[0].to_dict()
            return None
            
        result = etf_data.iloc[0].to_dict()
        
        # 尝试获取额外的基金信息
        try:
            fund_info = ak.fund_etf_fund_info_em(fund=stock_code)
            if fund_info is not None and not fund_info.empty:
                result.update(fund_info.iloc[0].to_dict())
        except:
            pass
            
        return result
        
    except Exception as e:
        logger.error(f"获取ETF信息失败: {e}")
        return None

def main():
    """主函数"""
    logger.info("开始检查ETF代码...")
    
    if not ETF_POOL:
        logger.error("ETF池为空")
        return
        
    results = []
    for code in ETF_POOL:
        logger.info(f"检查ETF代码: {code}")
        
        # 检查数据可用性
        available, details = check_stock_data_availability(code)
        
        # 获取ETF信息
        etf_info = get_etf_info(code)
        
        result = {
            "代码": code,
            "数据可用": available,
            "数据详情": details,
            "基本信息": etf_info
        }
        
        results.append(result)
        
        # 输出检查结果
        logger.info(f"ETF {code} 检查结果:")
        logger.info(f"数据可用: {'是' if available else '否'}")
        if isinstance(details, dict):
            for k, v in details.items():
                logger.info(f"{k}: {v}")
        else:
            logger.info(f"详情: {details}")
        if etf_info:
            logger.info("基本信息:")
            for k, v in etf_info.items():
                logger.info(f"{k}: {v}")
        logger.info("-" * 50)
    
    # 统计结果
    available_count = sum(1 for r in results if r["数据可用"])
    logger.info(f"检查完成: 共{len(ETF_POOL)}个ETF，{available_count}个可用")
    
    # 输出不可用的ETF
    unavailable = [r["代码"] for r in results if not r["数据可用"]]
    if unavailable:
        logger.warning(f"以下ETF数据不可用: {', '.join(unavailable)}")

if __name__ == "__main__":
    main() 