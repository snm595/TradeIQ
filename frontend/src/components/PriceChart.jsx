import { useEffect, useRef } from 'react';
import { createChart, CrosshairMode, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts';

export default function PriceChart({ data }) {
  const chartContainerRef = useRef();
  const chartRef = useRef(null);

  useEffect(() => {
    if (!data || data.length === 0 || !chartContainerRef.current) return;

    // Dark theme configuration
    const chartOptions = {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#9ab2d2',
      },
      grid: {
        vertLines: { color: 'rgba(73, 106, 146, 0.22)' },
        horzLines: { color: 'rgba(73, 106, 146, 0.22)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(72, 163, 255, 0.45)',
          width: 1,
          style: 2,
        },
        horzLine: {
          color: 'rgba(72, 163, 255, 0.35)',
          width: 1,
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(73, 106, 146, 0.5)',
      },
      timeScale: {
        borderColor: 'rgba(73, 106, 146, 0.5)',
        timeVisible: true,
        secondsVisible: false,
      },
      autoSize: true,
    };

    const chart = createChart(chartContainerRef.current, chartOptions);
    chartRef.current = chart;

    // Candlestick Series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#31d9a7',
      downColor: '#ff6a7a',
      borderVisible: false,
      wickUpColor: '#59e8be',
      wickDownColor: '#ff95a0',
    });

    const candleData = data.map(d => ({
      time: new Date(d.time).getTime() / 1000,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));
    candleSeries.setData(candleData);

    // VWAP Line Series
    const vwapSeries = chart.addSeries(LineSeries, {
      color: '#55aaff',
      lineWidth: 2,
      lineStyle: 0,
    });
    const vwapData = data.map(d => ({
      time: new Date(d.time).getTime() / 1000,
      value: d.vwap,
    })).filter(d => d.value != null);
    vwapSeries.setData(vwapData);

    // EMA 200 Line Series
    const emaSeries = chart.addSeries(LineSeries, {
      color: '#fbbd6f',
      lineWidth: 2,
      lineStyle: 2,
    });
    const emaData = data.map(d => ({
      time: new Date(d.time).getTime() / 1000,
      value: d.ema_200,
    })).filter(d => d.value != null);
    emaSeries.setData(emaData);

    // Markers for Signals
    const markers = [];
    data.forEach(d => {
      if (d.signal && d.decision === 'TRADE') {
        markers.push({
          time: new Date(d.time).getTime() / 1000,
          position: d.signal === 'BUY' ? 'belowBar' : 'aboveBar',
          color: d.signal === 'BUY' ? '#22c55e' : '#ef4444',
          shape: d.signal === 'BUY' ? 'arrowUp' : 'arrowDown',
          text: `${d.signal} ${Math.round(d.confidence_pct ?? 0)}%`,
        });
      }
    });
    createSeriesMarkers(candleSeries, markers);

    // Volume Histogram Series (pane 1)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '', // set as an overlay by setting a blank priceScaleId
      scaleMargins: {
        top: 0.8, // highest point of the series will be at 80% from the top
        bottom: 0,
      },
    });

    const volumeData = data.map(d => ({
      time: new Date(d.time).getTime() / 1000,
      value: d.volume,
      color: d.close >= d.open ? 'rgba(67, 219, 173, 0.30)' : 'rgba(255, 111, 130, 0.28)',
    }));
    volumeSeries.setData(volumeData);

    chart.timeScale().fitContent();

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
}
