import React from 'react';
import './Footer.css';

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-section">
          <h3>PoltuDa.in</h3>
          <p>Your trusted local service provider marketplace</p>
        </div>

        <div className="footer-section">
          <h4>Services</h4>
          <ul>
            <li><a href="/services">Plumber</a></li>
            <li><a href="/services">Electrician</a></li>
            <li><a href="/services">Carpenter</a></li>
            <li><a href="/services">Painter</a></li>
          </ul>
        </div>

        <div className="footer-section">
          <h4>Company</h4>
          <ul>
            <li><a href="/">About Us</a></li>
            <li><a href="/">Contact</a></li>
            <li><a href="/">Blog</a></li>
            <li><a href="/">Careers</a></li>
          </ul>
        </div>

        <div className="footer-section">
          <h4>Support</h4>
          <ul>
            <li><a href="/">Help Center</a></li>
            <li><a href="/">Privacy Policy</a></li>
            <li><a href="/">Terms of Service</a></li>
            <li><a href="/">Contact Us</a></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <p>&copy; 2024 PoltuDa.in. All rights reserved.</p>
      </div>
    </footer>
  );
}

export default Footer;
