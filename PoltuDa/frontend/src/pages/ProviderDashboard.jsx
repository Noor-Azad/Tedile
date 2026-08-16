import React, { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './Dashboard.css';

function ProviderDashboard({ user }) {
  const [activeTab, setActiveTab] = useState('profile');
  const [provider, setProvider] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProvider = async () => {
      try {
        const data = await apiClient.providers.getMyProfile();
        setProvider(data);
      } catch (error) {
        console.error('Error fetching provider profile:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProvider();
  }, []);

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await apiClient.providers.updateProfile({
        experience_years: provider.experience_years,
        hourly_rate: provider.hourly_rate,
        base_price: provider.base_price,
        availability_status: provider.availability_status,
      });

      setProvider(response.provider);
      alert('Profile updated successfully!');
    } catch (error) {
      alert('Error updating profile: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Provider Dashboard</h1>
        <p>Welcome, {user.first_name}!</p>
      </div>

      <div className="dashboard-tabs">
        <button
          className={`tab ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          My Profile
        </button>
        <button
          className={`tab ${activeTab === 'reviews' ? 'active' : ''}`}
          onClick={() => setActiveTab('reviews')}
        >
          Reviews & Rating
        </button>
        <button
          className={`tab ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          Jobs
        </button>
        <button
          className={`tab ${activeTab === 'offers' ? 'active' : ''}`}
          onClick={() => setActiveTab('offers')}
        >
          Offers
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'profile' && provider && (
          <div className="profile-section">
            <h2>My Profile</h2>
            <div className="rating-box">
              <div className="rating-stat">
                <h3>⭐ {provider.rating}</h3>
                <p>{provider.review_count} reviews</p>
              </div>
            </div>

            <form onSubmit={handleProfileUpdate} className="profile-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Service</label>
                  <input type="text" value={provider.service_name} disabled />
                </div>
                <div className="form-group">
                  <label>Experience (Years)</label>
                  <input
                    type="number"
                    value={provider.experience_years}
                    onChange={(e) =>
                      setProvider({
                        ...provider,
                        experience_years: parseInt(e.target.value),
                      })
                    }
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Hourly Rate (₹)</label>
                  <input
                    type="number"
                    value={provider.hourly_rate || ''}
                    onChange={(e) =>
                      setProvider({
                        ...provider,
                        hourly_rate: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="form-group">
                  <label>Base Price (₹)</label>
                  <input
                    type="number"
                    value={provider.base_price || ''}
                    onChange={(e) =>
                      setProvider({
                        ...provider,
                        base_price: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Availability Status</label>
                <select
                  value={provider.availability_status}
                  onChange={(e) =>
                    setProvider({
                      ...provider,
                      availability_status: e.target.value,
                    })
                  }
                >
                  <option value="available">Available</option>
                  <option value="busy">Busy</option>
                  <option value="unavailable">Unavailable</option>
                </select>
              </div>

              <button type="submit" className="submit-btn" disabled={loading}>
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>
        )}

        {activeTab === 'reviews' && provider && (
          <div className="reviews-section">
            <h2>Reviews & Rating</h2>
            <div className="stats">
              <div className="stat-card">
                <p>Average Rating</p>
                <h3>⭐ {provider.rating}</h3>
              </div>
              <div className="stat-card">
                <p>Total Reviews</p>
                <h3>{provider.review_count}</h3>
              </div>
            </div>

            {provider.recent_reviews && provider.recent_reviews.length > 0 ? (
              <div className="reviews-list">
                {provider.recent_reviews.map(review => (
                  <div key={review.id} className="review-card">
                    <div className="review-header">
                      <p className="reviewer-name">{review.customer_name}</p>
                      <span className="rating">⭐ {review.rating}</span>
                    </div>
                    <p className="review-title">{review.title}</p>
                    <p className="review-comment">{review.comment}</p>
                    <p className="review-date">
                      {new Date(review.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p>No reviews yet. Build your rating by completing jobs!</p>
            )}
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="jobs-section">
            <h2>My Jobs</h2>
            <p>No jobs assigned yet.</p>
          </div>
        )}

        {activeTab === 'offers' && (
          <div className="offers-section">
            <h2>My Offers</h2>
            <button className="btn">+ Create New Offer</button>
            {provider && provider.offers && provider.offers.length > 0 ? (
              <div className="offers-list">
                {provider.offers.map(offer => (
                  <div key={offer.id} className="offer-card">
                    <h4>{offer.title}</h4>
                    <p>{offer.description}</p>
                    {offer.discount_percentage && (
                      <p className="discount">🎉 {offer.discount_percentage}% OFF</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p>No offers created yet. Start by creating an offer!</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProviderDashboard;
