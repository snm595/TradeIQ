import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';

export default function PriceChart({ data }) {
  const option = useMemo(() => {
    if (!data || data.length === 0) return {};

    const candles = data.map((d) => [
      d.open,
      d.close,
      d.low,
      d.high,
    ]);

    const dates = data.map((d) =>
      new Date(d.time).toLocaleString()
    );

    const volume = data.map((d) => ({
      value: d.volume,
      itemStyle: {
        color:
          d.close >= d.open
            ? 'rgba(67,219,173,0.45)'
            : 'rgba(255,111,130,0.45)',
      },
    }));

    const vwap = data.map((d) => d.vwap ?? null);
    const ema = data.map((d) => d.ema_200 ?? null);

    const signalMarkers = data
      .filter((d) => d.signal && d.decision === 'TRADE')
      .map((d, idx) => ({
        name: d.signal,
        coord: [
          dates[idx],
          d.signal === 'BUY' ? d.low : d.high,
        ],
        value: `${d.signal} ${Math.round(
          d.confidence_pct ?? 0
        )}%`,
        itemStyle: {
          color:
            d.signal === 'BUY'
              ? '#22c55e'
              : '#ef4444',
        },
      }));

    return {
      backgroundColor: 'transparent',

      animation: true,

      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
        backgroundColor: '#07111f',
        borderColor: '#1f3b5c',
        textStyle: {
          color: '#dbe7ff',
        },
      },

      legend: {
        data: ['Candles', 'VWAP', 'EMA200'],
        textStyle: {
          color: '#94a3b8',
        },
      },

      grid: [
        {
          left: '4%',
          right: '2%',
          top: '8%',
          height: '68%',
        },
        {
          left: '4%',
          right: '2%',
          top: '80%',
          height: '12%',
        },
      ],

      xAxis: [
        {
          type: 'category',
          data: dates,
          boundaryGap: false,
          axisLine: {
            lineStyle: {
              color: '#355070',
            },
          },
          axisLabel: {
            color: '#94a3b8',
          },
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          boundaryGap: false,
          axisLine: {
            lineStyle: {
              color: '#355070',
            },
          },
          axisLabel: {
            show: false,
          },
        },
      ],

      yAxis: [
        {
          scale: true,
          axisLine: {
            lineStyle: {
              color: '#355070',
            },
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(80,120,170,0.15)',
            },
          },
          axisLabel: {
            color: '#94a3b8',
          },
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: {
            color: '#64748b',
          },
          splitLine: {
            show: false,
          },
        },
      ],

      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
        },
        {
          show: false,
          xAxisIndex: [0, 1],
          type: 'slider',
        },
      ],

      series: [
        {
          name: 'Candles',
          type: 'candlestick',
          data: candles,

          itemStyle: {
            color: '#31d9a7',
            color0: '#ff6a7a',
            borderColor: '#31d9a7',
            borderColor0: '#ff6a7a',
          },

          markPoint: {
            symbolSize: 48,
            label: {
              color: '#fff',
              fontWeight: 'bold',
            },
            data: signalMarkers,
          },
        },

        {
          name: 'VWAP',
          type: 'line',
          data: vwap,
          smooth: true,
          showSymbol: false,
          lineStyle: {
            width: 2,
            color: '#55aaff',
          },
        },

        {
          name: 'EMA200',
          type: 'line',
          data: ema,
          smooth: true,
          showSymbol: false,
          lineStyle: {
            width: 2,
            color: '#fbbd6f',
            type: 'dashed',
          },
        },

        {
          name: 'Volume',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volume,
        },
      ],
    };
  }, [data]);

  return (
    <div className="w-full h-full min-h-[620px]">
      <ReactECharts
        option={option}
        style={{
          height: '100%',
          width: '100%',
        }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
}