/**
 * API Client for PoltuDa.in
 * Handles all backend communication
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

class APIClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add token if available
    const token = localStorage.getItem('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'API request failed');
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Auth endpoints
  auth = {
    register: (userData) =>
      this.request('/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData),
      }),

    login: (email, password) =>
      this.request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    getMe: () =>
      this.request('/auth/me', {
        method: 'GET',
      }),

    updateProfile: (userData) =>
      this.request('/auth/profile', {
        method: 'PUT',
        body: JSON.stringify(userData),
      }),

    changePassword: (oldPassword, newPassword) =>
      this.request('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      }),
  };

  // Services endpoints
  services = {
    getAll: (page = 1, perPage = 20, filters = {}) => {
      const params = new URLSearchParams({
        page,
        per_page: perPage,
        ...filters,
      });
      return this.request(`/services?${params}`, { method: 'GET' });
    },

    getById: (serviceId) =>
      this.request(`/services/${serviceId}`, { method: 'GET' }),

    getProviders: (serviceId, page = 1, perPage = 20, filters = {}) => {
      const params = new URLSearchParams({
        page,
        per_page: perPage,
        ...filters,
      });
      return this.request(`/services/${serviceId}/providers?${params}`, {
        method: 'GET',
      });
    },

    searchByLocation: (latitude, longitude, serviceId = null, radius = 10) => {
      const params = new URLSearchParams({
        latitude,
        longitude,
        radius,
      });
      if (serviceId) params.append('service_id', serviceId);
      return this.request(`/services/search/by-location?${params}`, {
        method: 'GET',
      });
    },
  };

  // Providers endpoints
  providers = {
    getById: (providerId) =>
      this.request(`/providers/${providerId}`, { method: 'GET' }),

    getMyProfile: () =>
      this.request('/providers/me', { method: 'GET' }),

    updateProfile: (profileData) =>
      this.request('/providers/me', {
        method: 'PUT',
        body: JSON.stringify(profileData),
      }),

    search: (filters = {}, page = 1, perPage = 20) => {
      const params = new URLSearchParams({
        page,
        per_page: perPage,
        ...filters,
      });
      return this.request(`/providers?${params}`, { method: 'GET' });
    },

    getReviews: (providerId, page = 1, perPage = 10) => {
      const params = new URLSearchParams({
        page,
        per_page: perPage,
      });
      return this.request(`/providers/${providerId}/reviews?${params}`, {
        method: 'GET',
      });
    },

    addReview: (providerId, reviewData) =>
      this.request(`/providers/${providerId}/reviews`, {
        method: 'POST',
        body: JSON.stringify(reviewData),
      }),

    getOffers: (providerId) =>
      this.request(`/providers/${providerId}/offers`, { method: 'GET' }),
  };
}

// Create singleton instance
const apiClient = new APIClient();

export default apiClient;
