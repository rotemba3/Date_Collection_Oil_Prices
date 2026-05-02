import React, { useEffect, useState } from "react";

const PredictPage = () => {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/prediction/")
      .then((res) => res.json())
      .then((data) => {
        setPrediction(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching prediction:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={styles.container}>
        <h2>Loading prediction...</h2>
      </div>
    );
  }

  if (!prediction || prediction.error) {
    return (
      <div style={styles.container}>
        <h2>No prediction available</h2>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>📊 Oil Price Prediction</h1>

      <div style={styles.card}>
        <p><b>Prediction Date:</b> {prediction.prediction_date}</p>
        <p><b>Target Date:</b> {prediction.target_date}</p>
        <p><b>Based on Data Until:</b> {prediction.latest_data_date}</p>

        <hr />

        <h2 style={styles.prediction}>
          Predicted Range: {prediction.predicted_range}
        </h2>

        <p><b>Bin:</b> {prediction.predicted_bin}</p>

        <hr />

        <p><b>Last 3 Days Used:</b></p>
        <ul>
          {prediction.last3_dates.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>

        {prediction.actual_price && (
          <>
            <hr />
            <h3>Actual Result:</h3>
            <p>Price: {prediction.actual_price}</p>
            <p>
              Correct:{" "}
              {prediction.is_correct ? "✅ YES" : "❌ NO"}
            </p>
          </>
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: "40px",
    textAlign: "center",
    background: "#0f172a",
    minHeight: "100vh",
    color: "white",
  },
  title: {
    marginBottom: "30px",
  },
  card: {
    background: "#1e293b",
    padding: "30px",
    borderRadius: "12px",
    maxWidth: "500px",
    margin: "0 auto",
    boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
  },
  prediction: {
    color: "#38bdf8",
    marginTop: "10px",
  },
};

export default PredictPage;