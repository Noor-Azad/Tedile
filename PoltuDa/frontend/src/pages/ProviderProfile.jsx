import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../services/api';
import './ProviderProfile.css';

function ProviderProfile() {
  const { providerId } = useParams();
  const [provider, setProvider] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    const fetchProvider = async () => {
      try {
        const data = await apiClient.providers.getById(providerId);
        setProvider(data);
      } catch (error) {
        console.error('Error fetching provider:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProvider();
  }, [providerId]);

  if (loading) return <div className="loading">Loading...</div>;
  if (!provider) return <div className="error">Provider not found</div>;

  const user = provider.user;

  return (
    <div className="provider-profile">
      <div className="profile-header">
        <div className="profile-info">
          <h1>{user.first_name} {user.last_name}</h1>
          <p className="service">📍 {provider.service_name}</p>
          <div className="rating-badge">
            <span className="stars">⭐ {provider.rating}</span>
            <span className="review-count">({provider.review_count} reviews)</span>
          </div>
        </div>
      </div>

      <div className="profile-content">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={`tab ${activeTab === 'reviews' ? 'active' : ''}`}
            onClick={() => setActiveTab('reviews')}
          >
            Reviews
          </button>
          <button
            className={`tab ${activeTab === 'offers' ? 'active' : ''}`}
            onClick={() => setActiveTab('offers')}
          >
            Offers
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'overview' && (
            <div className="overview">
              <div className="info-grid">
                <div className="info-item">
                  <label>Experience</label>
                  <p>{provider.experience_years} years</p>
                </div>
                <div className="info-item">
                  <label>Hourly Rate</label>
                  <p>₹{provider.hourly_rate || 'N/A'}/hour</p>
                </div>
                <div className="info-item">
                  <label>Base Price</label>
                  <p>₹{provider.base_price || 'N/A'}</p>
                </div>
                <div className="info-item">
                  <label>Service Area</label>
                  <p>{provider.service_area_radius} km radius</p>
                </div>
              </div>

              <div className="bio-section">
                <h3>About</h3>
                <p>{user.bio || 'No bio provided'}</p>
              </div>

              <div className="contact-section">
                <h3>Contact</h3>
                <p>📞 <a href={`tel:${user.phone}`}>{user.phone}</a></p>
                <p>📧 {user.email}</p>
                <p>📍 {user.city}, {user.district}</p>

                <div className="contact-buttons">
                  <a href={`tel:${user.phone}`} className="btn primary">📞 Call Now</a>
                  <a href={`https://wa.me/${user.phone.replace(/\D/g, '')}`} className="btn">💬 WhatsApp</a>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'reviews' && (
            <div className="reviews">
              {provider.recent_reviews && provider.recent_reviews.length > 0 ? (
                provider.recent_reviews.map(review => (
                  <div key={review.id} className="review-card">
                    <div className="review-header">
                      <p className="reviewer-name">{review.customer_name}</p>
                      <span className="rating">⭐ {review.rating}</span>
                    </div>
                    <p className="review-title">{review.title}</p>
                    <p className="review-comment">{review.comment}</p>
                    <p className="review-date">{new Date(review.created_at).toLocaleDateString()}</p>
                  </div>
                ))
              ) : (
                <p>No reviews yet</p>
              )}
            </div>
          )}

          {activeTab === 'offers' && (
            <div className="offers">
              {provider.offers && provider.offers.length > 0 ? (
                provider.offers.map(offer => (
                  <div key={offer.id} className="offer-card">
                    <h4>{offer.title}</h4>
                    <p>{offer.description}</p>
                    {offer.discount_percentage && (
                      <p className="discount">🎉 {offer.discount_percentage}% OFF</p>
                    )}
                    {offer.discount_amount && (
                      <p className="discount">🎉 ₹{offer.discount_amount} OFF</p>
                    )}
                  </div>
                ))
              ) : (
                <p>No offers available</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProviderProfile;
