import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import GraphPage from "./Pages/graphpage";
import Nav_Bar from "./Components/Nav_Bar";
import Database_info from "./Pages/Database_info";

function App() {
  return(
    <Router>
      <Nav_Bar />
      <Routes>
        <Route path="/" element={<GraphPage />} />
        <Route path="/Data" element={<Database_info />} />
        {/* <Route path="/About" element={<AboutPage />} /> */}
      </Routes>
    </Router>
  );
}

export default App;