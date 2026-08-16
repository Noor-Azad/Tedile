import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

function Navbar({ user, isAuthenticated, onLogout }) {
  const handleLogout = () => {
    onLogout();
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          🏠 PoltuDa.in
        </Link>

        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/" className="nav-link">
              Home
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/services" className="nav-link">
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
                  <Link to="/dashboard" className="nav-link">
                    Dashboard
                  </Link>
                </li>
              )}
              {user?.user_type === 'provider' && (
                <li className="nav-item">
                  <Link to="/provider-dashboard" className="nav-link">
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
                <Link to="/login" className="nav-link">
                  Login
                </Link>
              </li>
              <li className="nav-item">
                <Link to="/register" className="nav-link signup">
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
