import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const analyzeSymbol = async (ticker, timeframe, period) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/analyze`, {
      params: { ticker, timeframe, period }
    });
    return response.data;
  } catch (error) {
    console.error('Error analyzing symbol:', error);
    throw error;
  }
};

export const backtestSymbol = async (ticker, timeframe, period) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/backtest`, {
      params: { ticker, timeframe, period }
    });
    return response.data;
  } catch (error) {
    console.error('Error backtesting symbol:', error);
    throw error;
  }
};
