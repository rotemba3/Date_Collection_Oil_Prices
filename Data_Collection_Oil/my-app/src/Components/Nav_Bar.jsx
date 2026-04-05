import React from 'react';
import '../Styles/Nav_Bar.css'; // We will create this next

export default function Navbar() {
    return (
        <nav className="navbar">
            <div className="nav-logo">Oil Prices changes</div>
            <ul className="nav-links">
                <li><a href="/">Dashboard</a></li>
                <li><a href="/Data">Data</a></li>
                <li><a href="/About">About</a></li>
            </ul>
        </nav>
    );
}

