import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../services/api';
import './ServiceDetails.css';

function ServiceDetails() {
  const { serviceId } = useParams();
  const [service, setService] = useState(null);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const serviceData = await apiClient.services.getById(serviceId);
        setService(serviceData);

        const providersData = await apiClient.services.getProviders(serviceId, page);
        setProviders(providersData.providers);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [serviceId, page]);

  if (loading) return <div className="loading">Loading...</div>;
  if (!service) return <div className="error">Service not found</div>;

  return (
    <div className="service-details">
      <div className="service-header">
        <span className="service-icon">{service.icon}</span>
        <h1>{service.name}</h1>
        <p>{service.description}</p>
      </div>

      <div className="providers-section">
        <h2>Available Providers</h2>
        {providers.length > 0 ? (
          <div className="providers-list">
            {providers.map(provider => (
              <div key={provider.id} className="provider-card">
                <h3>{provider.user.first_name} {provider.user.last_name}</h3>
                <p className="experience">Experience: {provider.experience_years} years</p>
                <p className="rating">⭐ {provider.rating} ({provider.review_count} reviews)</p>
                <p className="price">₹{provider.hourly_rate}/hour</p>
                <p className="location">📍 {provider.user.city}, {provider.user.district}</p>
                <div className="provider-actions">
                  <a href={`/provider/${provider.id}`} className="btn">View Profile</a>
                  <a href={`tel:${provider.user.phone}`} className="btn primary">📞 Call</a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p>No providers available for this service.</p>
        )}
      </div>
    </div>
  );
}

export default ServiceDetails;
