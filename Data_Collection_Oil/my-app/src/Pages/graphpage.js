import React, { useEffect, useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = [
  "#4F46E5", "#06B6D4", "#10B981", "#F59E0B",
  "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6",
  "#F97316", "#3B82F6"
];

function groupBy5Days(data) {
  if (!data || data.length === 0) return [];

  const sorted = [...data].sort(
    (a, b) => new Date(a.date) - new Date(b.date)
  );

  const grouped = [];

  for (let i = 0; i < sorted.length; i += 5) {
    const chunk = sorted.slice(i, i + 5);

    const date = chunk[0].date;

    const totalTweets = chunk.reduce(
      (sum, d) => sum + (Number(d.tweet_count) || 0),
      0
    );

    const validOil = chunk
      .map((d) => Number(d.oil_price))
      .filter((v) => !Number.isNaN(v));

    const avgOil =
      validOil.length > 0
        ? validOil.reduce((sum, v) => sum + v, 0) / validOil.length
        : null;

    grouped.push({
      date,
      tweet_count: totalTweets,
      oil_price: avgOil !== null ? Number(avgOil.toFixed(2)) : null,
    });
  }

  return grouped;
}

function groupByMonth(data) {
  if (!data || data.length === 0) return [];

  const monthlyMap = {};

  data.forEach((item) => {
    const d = new Date(item.date);
    if (Number.isNaN(d.getTime())) return;

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const key = `${year}-${month}`;

    if (!monthlyMap[key]) {
      monthlyMap[key] = {
        date: key,
        tweet_count: 0,
        oil_prices: [],
      };
    }

    monthlyMap[key].tweet_count += Number(item.tweet_count) || 0;

    const oil = Number(item.oil_price);
    if (!Number.isNaN(oil)) {
      monthlyMap[key].oil_prices.push(oil);
    }
  });

  return Object.values(monthlyMap)
    .map((item) => {
      const avgOil =
        item.oil_prices.length > 0
          ? item.oil_prices.reduce((sum, v) => sum + v, 0) / item.oil_prices.length
          : null;

      return {
        date: item.date,
        tweet_count: item.tweet_count,
        oil_price: avgOil !== null ? Number(avgOil.toFixed(2)) : null,
      };
    })
    .sort((a, b) => new Date(a.date + "-01") - new Date(b.date + "-01"));
}

function WordCloudLike({ data }) {
  if (!data || data.length === 0) {
    return <div>No word data available.</div>;
  }

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div
      style={{
        minHeight: 260,
        padding: 20,
        borderRadius: 20,
        background: "linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%)",
        border: "1px solid #dbeafe",
        display: "flex",
        flexWrap: "wrap",
        gap: "12px 18px",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {data.map((item, index) => {
        const size = 14 + (item.count / maxCount) * 30;
        const color = COLORS[index % COLORS.length];

        return (
          <span
            key={item.word}
            style={{
              fontSize: `${size}px`,
              fontWeight: 600,
              color,
              padding: "4px 8px",
              borderRadius: "999px",
              background: "rgba(255,255,255,0.7)",
              transform: `rotate(${(index % 5 - 2) * 6}deg)`,
            }}
          >
            {item.word}
          </span>
        );
      })}
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div
      style={{
        background: "white",
        borderRadius: 24,
        padding: 20,
        boxShadow: "0 10px 25px rgba(0,0,0,0.08)",
        marginBottom: 28,
      }}
    >
      <h2 style={{ marginBottom: 18, color: "#1e3a8a" }}>{title}</h2>
      {children}
    </div>
  );
}

export default function GraphPage() {
  const [commonWords, setCommonWords] = useState([]);
  const [tweetsVsOil, setTweetsVsOil] = useState([]);
  const [byPublisher, setByPublisher] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("http://127.0.0.1:8000/api/graph/common-words/").then((res) => res.json()),
      fetch("http://127.0.0.1:8000/api/graph/tweets-vs-oil/").then((res) => res.json()),
      fetch("http://127.0.0.1:8000/api/graph/tweets-vs-oil-by-publisher/").then((res) => res.json()),
    ])
      .then(([wordsData, tweetsOilData, byPublisherData]) => {
        setCommonWords(wordsData);
        setTweetsVsOil(groupBy5Days(tweetsOilData));

        const groupedPublishers = {};
        for (const key in byPublisherData) {
          groupedPublishers[key] = groupByMonth(byPublisherData[key]);
        }
        setByPublisher(groupedPublishers);
      })
      .catch((err) => {
        console.error("Error loading graph data:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ padding: 30 }}>Loading...</div>;
  }

  return (
    <div style={{ padding: 24, background: "#f1f5f9", minHeight: "100vh" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <h1 style={{ marginBottom: 20 }}>Graph Dashboard</h1>

        <Card title="Most Common Words">
          <WordCloudLike data={commonWords} />
        </Card>

        <Card title="Tweets vs Oil Price (Grouped by 5 Days)">
          <div style={{ height: 350 }}>
            <ResponsiveContainer>
              <ComposedChart data={tweetsVsOil}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Bar
                  yAxisId="left"
                  dataKey="tweet_count"
                  fill="#06B6D4"
                  name="Tweets"
                />
                <Line
                  yAxisId="right"
                  dataKey="oil_price"
                  stroke="#EF4444"
                  strokeWidth={3}
                  name="Oil Price"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="By Publisher (Monthly)">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              gap: 20,
            }}
          >
            {Object.keys(byPublisher).map((publisher, i) => (
              <div
                key={publisher}
                style={{
                  background: "white",
                  padding: 12,
                  borderRadius: 16,
                }}
              >
                <h3>{publisher}</h3>

                <div style={{ height: 250 }}>
                  <ResponsiveContainer>
                    <ComposedChart data={byPublisher[publisher]}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis yAxisId="left" />
                      <YAxis yAxisId="right" orientation="right" />
                      <Tooltip />
                      <Legend />
                      <Bar
                        yAxisId="left"
                        dataKey="tweet_count"
                        fill={COLORS[i % COLORS.length]}
                        name="Tweets"
                      />
                      <Line
                        yAxisId="right"
                        dataKey="oil_price"
                        stroke="#EF4444"
                        strokeWidth={2}
                        name="Oil Price"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}