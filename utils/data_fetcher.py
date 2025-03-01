"""
Data fetcher module for downloading and caching stock data
"""
import os
import pickle
import datetime
import pandas as pd
import akshare as ak
from loguru import logger

from config.config import CACHE_DIR, CACHE_EXPIRY_DAYS

class DataFetcher:
    """
    Data fetcher class for retrieving and caching stock data
    """
    def __init__(self):
        self.cache_dir = CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Data cache directory: {self.cache_dir}")
        
        # Cache for stock list
        self._stock_list_cache = None
        self._stock_list_cache_time = None
        
        # Cache for ETF list
        self._etf_list_cache = None
        self._etf_list_cache_time = None

    def _get_cache_path(self, stock_code, start_date, end_date, adjust):
        """
        Generate cache file path based on parameters
        """
        adjust_str = "qfq" if adjust == "qfq" else "hfq" if adjust == "hfq" else "none"
        filename = f"{stock_code}_{start_date}_{end_date}_{adjust_str}.pkl"
        return os.path.join(self.cache_dir, filename)

    def _is_cache_valid(self, cache_path):
        """
        Check if cache is valid and not expired
        """
        if not os.path.exists(cache_path):
            return False
        
        # Check if cache is expired
        file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(cache_path))
        expiry_time = datetime.datetime.now() - datetime.timedelta(days=CACHE_EXPIRY_DAYS)
        
        return file_mod_time > expiry_time
    
    def validate_stock_code(self, stock_code):
        """
        Validate if a stock code exists in A-shares market
        
        Parameters:
        -----------
        stock_code : str
            Stock code to validate
            
        Returns:
        --------
        bool
            True if stock code exists, False otherwise
        """
        try:
            # Get all stock codes
            all_stocks = self.get_all_stock_codes()
            
            # Check if the stock code exists
            if stock_code in all_stocks['代码'].values:
                logger.info(f"Stock code {stock_code} is valid")
                return True
            else:
                logger.warning(f"Stock code {stock_code} not found in A-shares market")
                logger.info("Available stock codes (first 10 shown):")
                logger.info(all_stocks['代码'].head(10).tolist())
                return False
                
        except Exception as e:
            logger.error(f"Error validating stock code: {e}")
            return False
    
    def validate_etf_code(self, etf_code):
        """
        Validate if an ETF code exists
        
        Parameters:
        -----------
        etf_code : str
            ETF code to validate
            
        Returns:
        --------
        bool
            True if ETF code exists, False otherwise
        """
        try:
            # Get all ETF codes
            all_etfs = self.get_all_etf_codes()
            
            # Check if the ETF code exists
            if etf_code in all_etfs['代码'].values:
                logger.info(f"ETF code {etf_code} is valid")
                return True
            else:
                logger.warning(f"ETF code {etf_code} not found")
                logger.info("Available ETF codes (first 10 shown):")
                logger.info(all_etfs['代码'].head(10).tolist())
                return False
                
        except Exception as e:
            logger.error(f"Error validating ETF code: {e}")
            return False
    
    def get_all_stock_codes(self):
        """
        Get all available A-shares stock codes using ak.stock_zh_a_spot_em()
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame containing all stock codes and names
        """
        # Check if we have a recent cache (less than 1 day old)
        if (self._stock_list_cache is not None and 
            self._stock_list_cache_time is not None and
            (datetime.datetime.now() - self._stock_list_cache_time).total_seconds() < 86400):
            return self._stock_list_cache
        
        try:
            logger.info("Fetching all A-shares stock codes from akshare")
            stock_df = ak.stock_zh_a_spot_em()
            
            # Cache the result
            self._stock_list_cache = stock_df
            self._stock_list_cache_time = datetime.datetime.now()
            
            logger.info(f"Retrieved {len(stock_df)} stock codes")
            return stock_df
            
        except Exception as e:
            logger.error(f"Error fetching stock codes: {e}")
            return pd.DataFrame(columns=['代码', '名称'])
    
    def get_all_etf_codes(self):
        """
        Get all available ETF codes using ak.fund_etf_spot_em()
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame containing all ETF codes and names
        """
        # Check if we have a recent cache (less than 1 day old)
        if (self._etf_list_cache is not None and 
            self._etf_list_cache_time is not None and
            (datetime.datetime.now() - self._etf_list_cache_time).total_seconds() < 86400):
            return self._etf_list_cache
        
        try:
            logger.info("Fetching all ETF codes from akshare")
            etf_df = ak.fund_etf_spot_em()
            
            # Cache the result
            self._etf_list_cache = etf_df
            self._etf_list_cache_time = datetime.datetime.now()
            
            logger.info(f"Retrieved {len(etf_df)} ETF codes")
            return etf_df
            
        except Exception as e:
            logger.error(f"Error fetching ETF codes: {e}")
            return pd.DataFrame(columns=['代码', '名称'])
    
    def print_all_stock_codes(self, limit=None):
        """
        Print all available A-shares stock codes
        
        Parameters:
        -----------
        limit : int
            Maximum number of stock codes to print (None for all)
        """
        try:
            stock_df = self.get_all_stock_codes()
            
            if limit is not None:
                stock_df = stock_df.head(limit)
                
            # Print stock codes and names
            for _, row in stock_df.iterrows():
                print(f"{row['代码']} - {row['名称']}")
                
            print(f"\nTotal: {len(stock_df)} stocks")
            
        except Exception as e:
            logger.error(f"Error printing stock codes: {e}")
    
    def print_all_etf_codes(self, limit=None):
        """
        Print all available ETF codes
        
        Parameters:
        -----------
        limit : int
            Maximum number of ETF codes to print (None for all)
        """
        try:
            etf_df = self.get_all_etf_codes()
            
            if limit is not None:
                etf_df = etf_df.head(limit)
                
            # Print ETF codes and names
            for _, row in etf_df.iterrows():
                print(f"{row['代码']} - {row['名称']}")
                
            print(f"\nTotal: {len(etf_df)} ETFs")
            
        except Exception as e:
            logger.error(f"Error printing ETF codes: {e}")

    def get_stock_data(self, stock_code, start_date, end_date, adjust="qfq"):
        """
        Get stock data with caching
        
        Parameters:
        -----------
        stock_code : str
            Stock code (e.g., "600000" for Shanghai Stock Exchange)
        start_date : str
            Start date in format "YYYY-MM-DD"
        end_date : str
            End date in format "YYYY-MM-DD"
        adjust : str
            Price adjustment method: "qfq" for forward adjustment,
            "hfq" for backward adjustment, None for no adjustment
            
        Returns:
        --------
        pandas.DataFrame
            Stock price data
        """
        # Validate stock code first
        if not self.validate_stock_code(stock_code):
            logger.warning(f"Invalid stock code: {stock_code}")
            return pd.DataFrame()
            
        cache_path = self._get_cache_path(stock_code, start_date, end_date, adjust)
        
        # Try to load from cache first
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"Loaded {stock_code} data from cache")
                return data
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        
        # Fetch data from akshare if cache is invalid or doesn't exist
        try:
            logger.info(f"Fetching {stock_code} data from akshare")
            
            # 修正：直接使用股票代码，不需要额外添加前缀
            # 根据最新的akshare API文档
            try:
                if adjust == "qfq":
                    data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                            start_date=start_date, end_date=end_date, 
                                            adjust="qfq")
                elif adjust == "hfq":
                    data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                            start_date=start_date, end_date=end_date, 
                                            adjust="hfq")
                else:
                    data = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                            start_date=start_date, end_date=end_date, 
                                            adjust="")
            except Exception as e:
                # 如果直接使用代码失败，尝试使用传统方式添加前缀
                logger.info(f"尝试使用传统格式获取 {stock_code} 数据")
                formatted_code = stock_code
                if stock_code.startswith('6'):
                    formatted_code = f"sh{stock_code}"
                elif stock_code.startswith(('0', '3')):
                    formatted_code = f"sz{stock_code}"
                
                if adjust == "qfq":
                    data = ak.stock_zh_a_hist(symbol=formatted_code, period="daily", 
                                            start_date=start_date, end_date=end_date, 
                                            adjust="qfq")
                elif adjust == "hfq":
                    data = ak.stock_zh_a_hist(symbol=formatted_code, period="daily", 
                                            start_date=start_date, end_date=end_date, 
                                            adjust="hfq")
                else:
                    data = ak.stock_zh_a_hist(symbol=formatted_code, period="daily", 
                                            start_date=start_date, end_date=end_date, 
                                            adjust="")
            
            # Ensure we got data and it has the expected format
            if data is None or len(data) == 0:
                logger.warning(f"No data returned for {stock_code}")
                return pd.DataFrame()
            
            # Rename columns to standardized format
            data = data.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # Convert date column to datetime
            data['date'] = pd.to_datetime(data['date'])
            
            # Set date as index
            data.set_index('date', inplace=True)
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching data for {stock_code}: {e}")
            return pd.DataFrame()
    
    def get_etf_data(self, etf_code, start_date=None, end_date=None, adjust=None):
        """
        Get ETF historical data
        
        Parameters:
        -----------
        etf_code : str
            ETF code (e.g., "510300" for 沪深300ETF)
        start_date : str, optional
            Start date in format 'YYYY-MM-DD'
        end_date : str, optional
            End date in format 'YYYY-MM-DD'
        adjust : str, optional
            Price adjustment: None (no adjustment), 'qfq' (forward adjustment), 'hfq' (backward adjustment)
            
        Returns:
        --------
        pandas.DataFrame
            ETF historical data
        """
        # 转换日期格式为YYYYMMDD
        start_date_fmt = start_date.replace('-', '') if start_date else '19700101'
        end_date_fmt = end_date.replace('-', '') if end_date else '20500101'
        
        cache_path = self._get_cache_path(f"ETF_{etf_code}", start_date, end_date, adjust)
        
        # Try to load from cache first
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"Loaded ETF {etf_code} data from cache")
                return data
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        
        # Fetch data from akshare if cache is invalid or doesn't exist
        try:
            logger.info(f"Fetching ETF {etf_code} data from akshare")
            
            # 使用fund_etf_hist_em获取ETF历史数据
            try:
                if adjust == "qfq":
                    data = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                             start_date=start_date_fmt, end_date=end_date_fmt, 
                                             adjust="qfq")
                elif adjust == "hfq":
                    data = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                             start_date=start_date_fmt, end_date=end_date_fmt, 
                                             adjust="hfq")
                else:
                    data = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                             start_date=start_date_fmt, end_date=end_date_fmt, 
                                             adjust="")
            except Exception as e:
                logger.error(f"Error fetching ETF data: {e}")
                return pd.DataFrame()
            
            # Ensure we got data and it has the expected format
            if data is None or len(data) == 0:
                logger.warning(f"No data returned for ETF {etf_code}")
                return pd.DataFrame()
            
            # Rename columns to standardized format
            data = data.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # Convert date column to datetime
            data['date'] = pd.to_datetime(data['date'])
            
            # Set date as index
            data.set_index('date', inplace=True)
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            return data
        
        except Exception as e:
            logger.error(f"Error fetching data for ETF {etf_code}: {e}")
            return pd.DataFrame()
    
    def get_index_data(self, index_code, start_date, end_date):
        """
        Get index data (such as CSI 300, SSE Composite)
        
        Parameters:
        -----------
        index_code : str
            Index code (e.g., "000300" for CSI 300, "000001" for SSE Composite)
            
        Returns:
        --------
        pandas.DataFrame
            Index data
        """
        cache_path = self._get_cache_path(f"IDX_{index_code}", start_date, end_date, None)
        
        # Try to load from cache first
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"Loaded {index_code} index data from cache")
                return data
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        
        # Fetch data from akshare if cache is invalid or doesn't exist
        try:
            logger.info(f"Fetching {index_code} index data from akshare")
            
            # 修正：直接使用指数代码，不需要额外前缀
            try:
                data = ak.stock_zh_index_daily(symbol=index_code)
            except Exception as e:
                # 如果直接使用代码失败，尝试传统方式添加前缀
                logger.info(f"尝试使用传统格式获取 {index_code} 指数数据")
                if index_code.startswith('0'):
                    index_symbol = f"sh{index_code}"
                elif index_code.startswith('3'):
                    index_symbol = f"sz{index_code}"
                else:
                    index_symbol = index_code
                    
                data = ak.stock_zh_index_daily(symbol=index_symbol)
            
            # Filter by date
            data['date'] = pd.to_datetime(data['date'])
            mask = (data['date'] >= pd.to_datetime(start_date)) & (data['date'] <= pd.to_datetime(end_date))
            data = data[mask]
            
            # Rename columns
            data = data.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Set date as index
            data.set_index('date', inplace=True)
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching index data for {index_code}: {e}")
            return pd.DataFrame()
    
    def get_all_stocks(self):
        """
        Get a list of all available A-share stocks
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame containing stock codes and names
        """
        cache_path = os.path.join(self.cache_dir, "all_stocks.pkl")
        
        # Try to load from cache first
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                logger.info("Loaded all stocks list from cache")
                return data
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        
        # Fetch data from akshare
        try:
            logger.info("Fetching all stocks list from akshare")
            
            # Get stocks from Shanghai Stock Exchange
            sh_stocks = ak.stock_info_sh_name_code()
            sh_stocks['exchange'] = 'SH'
            
            # Get stocks from Shenzhen Stock Exchange
            sz_stocks = ak.stock_info_sz_name_code()
            sz_stocks['exchange'] = 'SZ'
            
            # Combine them
            all_stocks = pd.concat([sh_stocks, sz_stocks])
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                pickle.dump(all_stocks, f)
            
            return all_stocks
            
        except Exception as e:
            logger.error(f"Error fetching all stocks list: {e}")
            return pd.DataFrame() 