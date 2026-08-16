import React, { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './Dashboard.css';

function Dashboard({ user }) {
  const [activeTab, setActiveTab] = useState('profile');
  const [profileData, setProfileData] = useState(user);
  const [loading, setLoading] = useState(false);

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await apiClient.auth.updateProfile({
        first_name: profileData.first_name,
        last_name: profileData.last_name,
        phone: profileData.phone,
        bio: profileData.bio,
        city: profileData.city,
        district: profileData.district,
      });

      setProfileData(response.user);
      alert('Profile updated successfully!');
    } catch (error) {
      alert('Error updating profile: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Customer Dashboard</h1>
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
          className={`tab ${activeTab === 'bookings' ? 'active' : ''}`}
          onClick={() => setActiveTab('bookings')}
        >
          My Bookings
        </button>
        <button
          className={`tab ${activeTab === 'reviews' ? 'active' : ''}`}
          onClick={() => setActiveTab('reviews')}
        >
          My Reviews
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'profile' && (
          <div className="profile-section">
            <h2>My Profile</h2>
            <form onSubmit={handleProfileUpdate} className="profile-form">
              <div className="form-row">
                <div className="form-group">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={profileData.first_name}
                    onChange={(e) =>
                      setProfileData({ ...profileData, first_name: e.target.value })
                    }
                  />
                </div>
                <div className="form-group">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={profileData.last_name}
                    onChange={(e) =>
                      setProfileData({ ...profileData, last_name: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Email</label>
                <input type="email" value={profileData.email} disabled />
              </div>

              <div className="form-group">
                <label>Phone</label>
                <input
                  type="tel"
                  value={profileData.phone}
                  onChange={(e) =>
                    setProfileData({ ...profileData, phone: e.target.value })
                  }
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>City</label>
                  <input
                    type="text"
                    value={profileData.city || ''}
                    onChange={(e) =>
                      setProfileData({ ...profileData, city: e.target.value })
                    }
                  />
                </div>
                <div className="form-group">
                  <label>District</label>
                  <input
                    type="text"
                    value={profileData.district || ''}
                    onChange={(e) =>
                      setProfileData({ ...profileData, district: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Bio</label>
                <textarea
                  value={profileData.bio || ''}
                  onChange={(e) =>
                    setProfileData({ ...profileData, bio: e.target.value })
                  }
                  rows="4"
                />
              </div>

              <button type="submit" className="submit-btn" disabled={loading}>
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>
        )}

        {activeTab === 'bookings' && (
          <div className="bookings-section">
            <h2>My Bookings</h2>
            <p>No bookings yet. <a href="/services">Browse services</a></p>
          </div>
        )}

        {activeTab === 'reviews' && (
          <div className="reviews-section">
            <h2>My Reviews</h2>
            <p>You haven't left any reviews yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
