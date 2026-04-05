import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../Styles/Database_info.css';

export default function DatabaseInfo() {
    const [data, setData] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        axios.get('http://127.0.0.1:8000/get-all-data/')
            .then(res => setData(res.data))
            .catch(err => console.error(err));
    }, []);

    const filteredData = data.filter(item => 
        item.publisher.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.date.includes(searchTerm)
    );

    return (
        <div className="database-container">
            <h2>MongoDB Records</h2>
            
            <input 
                type="text" 
                placeholder="Filter by Publisher or Date (YYYY-MM-DD)..." 
                className="filter-input"
                onChange={(e) => setSearchTerm(e.target.value)}
            />

            <table className="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Publisher</th>
                        <th>Oil Price</th>
                        <th>Gas Price</th>
                        <th>Change %</th>
                    </tr>
                </thead>
                <tbody>
                    {filteredData.map((item, index) => (
                        <tr key={index}>
                            <td>{item.date}</td>
                            <td>{item.publisher}</td>
                            <td>${item.oil_price}</td>
                            <td>${item.gas_price}</td>
                            <td>{item.oil_change_percent}%</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}