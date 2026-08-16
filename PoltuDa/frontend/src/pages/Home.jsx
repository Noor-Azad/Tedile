import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../services/api';
import './Home.css';

function Home() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState('');
  const [locationInput, setLocationInput] = useState('');

  useEffect(() => {
    const fetchServices = async () => {
      try {
        const data = await apiClient.services.getAll(1, 10);
        setServices(data.services);
      } catch (error) {
        console.error('Error fetching services:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchServices();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    // Handle search - will redirect to services page with filters
    window.location.href = `/services?search=${searchInput}`;
  };

  return (
    <div className="home">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <h1>Find Skilled Professionals Near You</h1>
          <p>Connect with trusted local service providers instantly</p>

          <form className="search-form" onSubmit={handleSearch}>
            <div className="search-inputs">
              <input
                type="text"
                placeholder="Search services (plumber, electrician...)"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="search-input"
              />
              <input
                type="text"
                placeholder="Enter location or city"
                value={locationInput}
                onChange={(e) => setLocationInput(e.target.value)}
                className="search-input"
              />
              <button type="submit" className="search-btn">
                🔍 Search
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Services Section */}
      <section className="services-section">
        <div className="section-header">
          <h2>Popular Services</h2>
          <Link to="/services" className="view-all-link">
            View All Services →
          </Link>
        </div>

        {loading ? (
          <div className="loading">Loading services...</div>
        ) : (
          <div className="services-grid">
            {services.map((service) => (
              <Link
                key={service.id}
                to={`/services/${service.id}`}
                className="service-card"
              >
                <div className="service-icon">{service.icon}</div>
                <h3>{service.name}</h3>
                <p>{service.description?.substring(0, 50)}...</p>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Features Section */}
      <section className="features">
        <h2>Why Choose PoltuDa.in?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">✓</div>
            <h3>Verified Professionals</h3>
            <p>All providers are verified and reviewed by customers</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📍</div>
            <h3>Location-Based Search</h3>
            <p>Find professionals near you instantly</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⭐</div>
            <h3>Ratings & Reviews</h3>
            <p>Make informed decisions with real customer feedback</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>Direct Contact</h3>
            <p>Connect directly via phone or WhatsApp</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2>Ready to Find Help?</h2>
        <div className="cta-buttons">
          <Link to="/services" className="cta-btn primary">
            Browse Services
          </Link>
          <Link to="/register" className="cta-btn secondary">
            Become a Provider
          </Link>
        </div>
      </section>
    </div>
  );
}

export default Home;
