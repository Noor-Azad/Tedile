import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import apiClient from '../services/api';
import './Services.css';

function Services() {
  const [searchParams] = useSearchParams();
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState(searchParams.get('search') || '');

  useEffect(() => {
    const fetchServices = async () => {
      setLoading(true);
      try {
        const data = await apiClient.services.getAll(page, 20, search ? { search } : {});
        setServices(data.services);
        setTotalPages(data.pages);
      } catch (error) {
        console.error('Error fetching services:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchServices();
  }, [page, search]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <div className="services-page">
      <div className="page-header">
        <h1>Services</h1>
        <p>Browse and find trusted service providers</p>
      </div>

      <div className="services-container">
        <aside className="filters">
          <form onSubmit={handleSearch}>
            <div className="filter-group">
              <label htmlFor="search">Search Services</label>
              <input
                id="search"
                type="text"
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button type="submit">Search</button>
            </div>
          </form>
        </aside>

        <main className="services-list">
          {loading ? (
            <div className="loading">Loading services...</div>
          ) : services.length > 0 ? (
            <>
              <div className="services-results">
                {services.map((service) => (
                  <div key={service.id} className="service-result">
                    <div className="service-icon">{service.icon}</div>
                    <div className="service-content">
                      <h2>
                        <a href={`/services/${service.id}`}>{service.name}</a>
                      </h2>
                      <p>{service.description}</p>
                      <a href={`/services/${service.id}`} className="view-providers-btn">
                        View Providers →
                      </a>
                    </div>
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="pagination">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                  >
                    ← Previous
                  </button>
                  <span>{page} / {totalPages}</span>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="no-results">
              <p>No services found. Try different search terms.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default Services;
