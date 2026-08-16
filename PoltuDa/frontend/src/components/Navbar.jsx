import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

function Navbar({ user, isAuthenticated, onLogout }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleLogout = () => {
    onLogout();
    setIsMenuOpen(false);
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          🏠 PoltuDa.in
        </Link>

        <button
          className="menu-toggle"
          type="button"
          aria-label="Toggle navigation menu"
          aria-expanded={isMenuOpen}
          onClick={() => setIsMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>

        <ul className={`nav-menu${isMenuOpen ? ' is-open' : ''}`}>
          <li className="nav-item">
            <Link to="/" className="nav-link" onClick={() => setIsMenuOpen(false)}>
              Home
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/services" className="nav-link" onClick={() => setIsMenuOpen(false)}>
              Services
            </Link>
          </li>
          
          {isAuthenticated ? (
            <>
              <li className="nav-item">
                <span className="nav-user">👤 {user?.first_name}</span>
              </li>
              {user?.user_type === 'customer' && (
                <li className="nav-item">
                  <Link to="/dashboard" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                    Dashboard
                  </Link>
                </li>
              )}
              {user?.user_type === 'provider' && (
                <li className="nav-item">
                  <Link to="/provider-dashboard" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                    Dashboard
                  </Link>
                </li>
              )}
              <li className="nav-item">
                <button onClick={handleLogout} className="nav-link logout-btn">
                  Logout
                </button>
              </li>
            </>
          ) : (
            <>
              <li className="nav-item">
                <Link to="/login" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                  Login
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/register" className="nav-link signup" onClick={() => setIsMenuOpen(false)}>
                  Sign Up
                </Link>
              </li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
}

export default Navbar;
