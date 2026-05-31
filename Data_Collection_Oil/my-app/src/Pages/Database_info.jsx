import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../Styles/Database_info.css';

const PAGE_SIZE = 20;

export default function DatabaseInfo() {
    const [data, setData]           = useState([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [page, setPage]           = useState(1);

    useEffect(() => {
        axios.get('http://127.0.0.1:8000/api/get-all-data/')
            .then(res => setData(res.data))
            .catch(err => console.error(err));
    }, []);

    // Reset to page 1 whenever filter changes
    useEffect(() => { setPage(1); }, [searchTerm]);

    const formatDisplayDate = (dateString) => {
        if (!dateString) return "N/A";
        return dateString.split('-').reverse().join('-');
    };

    const filteredData = data.filter(item => {
        const publisher   = item.publisher  ? String(item.publisher).toLowerCase()  : "";
        const date        = item.date       ? String(item.date)                      : "";
        const textContent = item.text       ? String(item.text).toLowerCase()        : "";
        const term        = searchTerm.toLowerCase();
        return publisher.includes(term) || date.includes(term) || textContent.includes(term);
    });

    const totalPages  = Math.max(1, Math.ceil(filteredData.length / PAGE_SIZE));
    const safePage    = Math.min(page, totalPages);
    const pageData    = filteredData.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

    const goTo   = (p) => setPage(Math.max(1, Math.min(p, totalPages)));
    const pageNumbers = () => {
        // show at most 5 page buttons around current page
        const pages = [];
        const start = Math.max(1, safePage - 2);
        const end   = Math.min(totalPages, start + 4);
        for (let i = start; i <= end; i++) pages.push(i);
        return pages;
    };

    return (
        <div className="database-container">
            <h2>Oil and Gas changes</h2>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <input
                    type="text"
                    placeholder="Filter by Publisher, Date or Content..."
                    className="filter-input"
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{ flex: 1 }}
                />
                <span style={{ color: '#666', whiteSpace: 'nowrap', fontSize: 14 }}>
                    {filteredData.length} rows
                </span>
            </div>

            <div style={{ maxHeight: 500, overflowY: "auto", border: "1px solid #e5e7eb", borderRadius: 10 }}>
            <table className="data-table" style={{ width: "100%" }}>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Date</th>
                        <th>Publisher</th>
                        <th>Content</th>
                        <th>Oil Price</th>
                        <th>Gas Price</th>
                        <th>Change %</th>
                    </tr>
                </thead>
                <tbody>
                    {pageData.map((item, index) => (
                        <tr key={index}>
                            <td style={{ fontWeight: 'bold', color: '#666' }}>
                                {(safePage - 1) * PAGE_SIZE + index + 1}
                            </td>
                            <td>{formatDisplayDate(item.date)}</td>
                            <td>{item.publisher}</td>
                            <td className="text-cell">{item.text || "No content available"}</td>
                            <td>{item.oil_price   ? `$${item.oil_price}`           : "None"}</td>
                            <td>{item.gas_price   ? `$${item.gas_price}`           : "None"}</td>
                            <td>{item.oil_change_percent ? `${item.oil_change_percent}%` : "None"}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
            </div>

            {/* ── Pagination controls ── */}
            <div style={paginationStyle.wrapper}>
                <button
                    onClick={() => goTo(1)}
                    disabled={safePage === 1}
                    style={paginationStyle.btn}
                >«</button>

                <button
                    onClick={() => goTo(safePage - 1)}
                    disabled={safePage === 1}
                    style={paginationStyle.btn}
                >‹ Prev</button>

                {pageNumbers().map(p => (
                    <button
                        key={p}
                        onClick={() => goTo(p)}
                        style={{
                            ...paginationStyle.btn,
                            ...(p === safePage ? paginationStyle.active : {})
                        }}
                    >{p}</button>
                ))}

                <button
                    onClick={() => goTo(safePage + 1)}
                    disabled={safePage === totalPages}
                    style={paginationStyle.btn}
                >Next ›</button>

                <button
                    onClick={() => goTo(totalPages)}
                    disabled={safePage === totalPages}
                    style={paginationStyle.btn}
                >»</button>

                <span style={{ marginLeft: 12, color: '#666', fontSize: 13 }}>
                    Page {safePage} of {totalPages}
                </span>
            </div>
        </div>
    );
}

const paginationStyle = {
    wrapper: {
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        marginTop: 16,
        flexWrap: 'wrap',
    },
    btn: {
        padding: '6px 12px',
        border: '1px solid #d1d5db',
        borderRadius: 8,
        background: 'white',
        cursor: 'pointer',
        fontSize: 13,
        color: '#374151',
    },
    active: {
        background: '#1d4ed8',
        color: 'white',
        borderColor: '#1d4ed8',
        fontWeight: 700,
    },
};