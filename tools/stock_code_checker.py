"""
股票代码检查工具
"""
import os
import sys
import argparse
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目模块
from utils.logger import setup_logger
from utils.data_fetcher import DataFetcher

def main():
    """
    股票代码检查工具的主入口
    """
    # 设置日志
    setup_logger()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='A股股票代码检查工具')
    
    # 命令选项
    parser.add_argument('--check', type=str, help='检查特定股票代码是否存在')
    parser.add_argument('--list', action='store_true', help='列出所有可用的股票代码')
    parser.add_argument('--limit', type=int, default=20, help='限制显示的代码数量')
    parser.add_argument('--etf', action='store_true', help='查询ETF基金而非股票')
    parser.add_argument('--check-etf', type=str, help='检查特定ETF代码是否存在')
    parser.add_argument('--list-etf', action='store_true', help='列出所有可用的ETF代码')
    
    args = parser.parse_args()
    
    # 创建数据获取器
    data_fetcher = DataFetcher()
    
    # ETF模式
    if args.etf or args.check_etf or args.list_etf:
        # 检查特定ETF代码
        if args.check_etf:
            logger.info(f"检查ETF代码: {args.check_etf}")
            if data_fetcher.validate_etf_code(args.check_etf):
                print(f"✅ ETF代码 '{args.check_etf}' 有效。")
            else:
                print(f"❌ ETF代码 '{args.check_etf}' 无效。")
                print("\n以下是一些可用的ETF代码:")
                data_fetcher.print_all_etf_codes(limit=10)
        
        # 列出所有ETF代码
        elif args.list_etf or args.etf:
            logger.info(f"列出ETF代码 (限制: {args.limit})")
            print(f"列出 {args.limit if args.limit else '所有'} 可用的ETF代码:")
            data_fetcher.print_all_etf_codes(limit=args.limit)
    
    # 股票模式（默认）
    else:
        # 检查特定股票代码
        if args.check:
            logger.info(f"检查股票代码: {args.check}")
            if data_fetcher.validate_stock_code(args.check):
                print(f"✅ 股票代码 '{args.check}' 有效。")
            else:
                print(f"❌ 股票代码 '{args.check}' 无效。")
                print("\n以下是一些可用的股票代码:")
                data_fetcher.print_all_stock_codes(limit=10)
        
        # 列出所有股票代码
        elif args.list:
            logger.info(f"列出股票代码 (限制: {args.limit})")
            print(f"列出 {args.limit if args.limit else '所有'} 可用的股票代码:")
            data_fetcher.print_all_stock_codes(limit=args.limit)
        
        # 未指定命令
        else:
            parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("程序被用户终止")
    except Exception as e:
        logger.exception(f"意外错误: {e}")
        sys.exit(1) 