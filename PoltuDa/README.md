# PoltuDa.in - Local Service Provider Marketplace

A platform that connects users with independent, local service professionals (plumbers, electricians, carpenters, painters, etc.) in their area.

## 🎯 Project Goal

Build a location-based marketplace where:
- **Customers** can find and connect with local service providers
- **Providers** can list their services and build their business
- **Direct contact** happens between users and providers (no intermediaries)
- **Community-driven** with ratings, reviews, and verified professionals

## 📋 Key Features

- 🔍 Service browsing by category & location
- 📍 Location-based search with map integration
- ⭐ Rating & review system
- 👥 Provider profiles with specializations
- 📱 Direct WhatsApp/phone contact
- 💼 Provider verification & ratings
- 📝 Blog & tips section
- 🎁 Offers & deals from local providers
- 👨‍💼 Admin dashboard

## 🏗️ Project Structure

```
poltuda/
├── backend/          # Flask REST API
│   ├── app/
│   ├── models/       # Database models
│   ├── routes/       # API endpoints
│   └── config.py
├── frontend/         # React.js / Vue.js
│   ├── src/
│   ├── components/
│   └── pages/
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variables template
└── POLTUDA_DEVELOPMENT_PLAN.md  # Detailed development plan
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- PostgreSQL with PostGIS extension
- Node.js 16+
- Virtual environment (venv)

### Backend Setup

1. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database**
   ```bash
   # Create .env file with:
   DATABASE_URL=postgresql://user:password@localhost/poltuda_db
   JWT_SECRET_KEY=your_secret_key
   ```

4. **Initialize database**
   ```bash
   python manage.py db upgrade
   ```

5. **Run development server**
   ```bash
   python app.py
   ```
   Server runs at: `http://localhost:5000`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

## Free Testing Deployment

The project can be deployed as one mobile-friendly web app on Render's free web
service. The included `render.yaml` installs dependencies and starts Flask with
Gunicorn. The Flask app serves `index.html` and the API from the same URL, so
the app also works on a phone without changing the API address.

1. Create a GitHub repository and upload this project. Do not upload `venv/`,
   `.env`, or the SQLite database.
2. In Render, choose **New + > Blueprint** and connect the GitHub repository.
3. Deploy the generated `poltuda` web service using the included `render.yaml`.
4. Open the generated `https://...onrender.com` URL on your phone.

The free service may sleep when unused and its local SQLite data can reset when
the service is redeployed. This option is suitable for testing only.

On Android, use the browser menu and choose **Add to Home screen**. On iPhone,
open the URL in Safari, tap **Share**, then choose **Add to Home Screen**.

## Android and iOS Builds

The `mobile` directory contains a Capacitor wrapper connected to the deployed
web app. From that directory, install Node.js dependencies and add the native
platforms:

```bash
cd mobile
npm install
npx cap add android
npx cap add ios
npx cap sync
```

Open Android Studio with `npm run android:open` to build an APK. Open Xcode
with `npm run ios:open` to build and sign the iOS app. Android testing can use
an unsigned/debug APK; iOS device installation requires Apple signing.

## 📖 For Detailed Development Process

See [POLTUDA_DEVELOPMENT_PLAN.md](POLTUDA_DEVELOPMENT_PLAN.md) for:
- Technology stack recommendations
- Project phases & timeline
- Database schema design
- Core modules breakdown
- Deployment strategy

## 🔧 Tech Stack

**Backend:** Flask, PostgreSQL (with PostGIS), SQLAlchemy
**Frontend:** React.js or Vue.js, Tailwind CSS
**Maps:** Google Maps API / Mapbox
**Hosting:** AWS / DigitalOcean / Render
**Database:** PostgreSQL with PostGIS for geolocation

## 📝 Development Phases

1. **Foundation** (Weeks 1-2): Database, API, Authentication
2. **Core Features** (Weeks 3-4): Services, Providers, Search
3. **Frontend** (Weeks 5-6): UI/UX Implementation
4. **Additional Features** (Weeks 7-8): Blog, Offers, Admin Panel
5. **Launch** (Week 9+): Testing, Security, Deployment

## 🐛 Contributing

1. Create feature branch (`git checkout -b feature/feature-name`)
2. Commit changes (`git commit -m 'Add feature'`)
3. Push to branch (`git push origin feature/feature-name`)
4. Create Pull Request

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## 📞 Support

For questions or issues, please create an issue in the repository or contact the development team.

---

**Status:** 🚧 In Development
**Version:** 0.1.0 (Initial Setup)
