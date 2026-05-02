import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../Styles/Database_info.css';

export default function DatabaseInfo() {
    const [data, setData] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        axios.get('http://127.0.0.1:8000/api/get-all-data/')
            .then(res => setData(res.data))
            .catch(err => console.error(err));
    }, []);

    const formatDisplayDate = (dateString) => {
        if (!dateString) return "N/A";
        // Splits "2026-04-06" into ["2026", "04", "06"], reverses it, and joins with "-"
        return dateString.split('-').reverse().join('-');
    };

    const filteredData = data.filter(item => {
        const publisher = item.publisher ? String(item.publisher).toLowerCase() : "";
        const date = item.date ? String(item.date) : "";
        const textContent = item.text ? String(item.text).toLowerCase() : "";
        
        return publisher.includes(searchTerm.toLowerCase()) || date.includes(searchTerm) || textContent.includes(searchTerm.toLowerCase());
    });

    return (
        <div className="database-container">
            <h2>Oil and Gas changes</h2>
            
            <input 
                type="text" 
                placeholder="Filter by Publisher or Date (DD-MM-YYYY)..." 
                className="filter-input"
                onChange={(e) => setSearchTerm(e.target.value)}
            />

            <table className="data-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Date</th>
                        <th>Publisher</th>
                        <td>Content</td>
                        <th>Oil Price</th>
                        <th>Gas Price</th>
                        <th>Change %</th>
                    </tr>
                </thead>
                <tbody>
                    {filteredData.map((item, index) => (
                        <tr key={index}>
                            <td style={{ fontWeight: 'bold', color: '#666' }}>{index + 1}</td>
                            <td>{formatDisplayDate(item.date)}</td>
                            <td>{item.publisher}</td>
                            <td className="text-cell">
                                {item.text || "No content available"}
                            </td>
                            <td>{item.oil_price ? `$${item.oil_price}` : "None"}</td>
                            <td>{item.gas_price ? `$${item.gas_price}` : "None"}</td>
                            <td>{item.oil_change_percent ? `${item.oil_change_percent}%` : "None"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    ); 
}