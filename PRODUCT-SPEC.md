# PRODUCT-SPEC: Marketing

## Overview

**App Name:** Marketing
**Domain:** Email campaigns, landing pages, analytics
**Target User:** Marketing teams, growth hackers

## Core Entities

### Campaign
```
Campaign
├── id: UUID (PK)
├── name: str (required)
├── type: enum ["email", "social", "ppc", "content"] (required)
├── status: enum ["draft", "scheduled", "active", "paused", "completed"] (default: "draft")
├── start_date: date (optional)
├── end_date: date (optional)
├── budget: float (optional)
├── description: str (optional)
├── created_at: datetime
└── updated_at: datetime
```

### Lead
```
Lead
├── id: UUID (PK)
├── email: str (unique, required)
├── first_name: str (optional)
├── last_name: str (optional)
├── company: str (optional)
├── source: str (optional)
├── status: enum ["new", "contacted", "qualified", "converted", "lost"] (default: "new")
├── campaign_id: UUID (FK → Campaign, optional)
├── created_at: datetime
└── updated_at: datetime
```

### AnalyticsEvent
```
AnalyticsEvent
├── id: UUID (PK)
├── campaign_id: UUID (FK → Campaign, ondelete=CASCADE)
├── event_type: enum ["impression", "click", "conversion", "bounce"] (required)
├── value: float (default 0)
├── recorded_at: datetime
└── created_at: datetime
```

## User Stories / Screens

### Screen 1: Dashboard
- Summary cards: active campaigns, total leads, conversion rate (mock), total spend
- Campaign performance chart (mock)
- Recent leads list

### Screen 2: Campaigns
- Table/card view with campaign name, type, status, dates
- Status filter
- "Create Campaign" form

### Screen 3: Campaign Detail
- Campaign info with edit/delete
- Lead list for this campaign
- Analytics summary (impressions, clicks, conversions — mock data)

### Screen 4: Leads
- Table view with search, source filter, status filter
- "Add Lead" form
- Bulk status change (mock)

## AI Features

- **Lead scoring:** Score leads 1-100 based on attributes (mock algorithm)
- **Campaign optimization:** Suggest best send time (mock)

## API Endpoints (v1.0)

```
GET    /api/v1/campaigns          → List campaigns
POST   /api/v1/campaigns          → Create campaign
GET    /api/v1/campaigns/{id}     → Get campaign
PUT    /api/v1/campaigns/{id}     → Update campaign
DELETE /api/v1/campaigns/{id}     → Delete campaign
GET    /api/v1/leads              → List leads
POST   /api/v1/leads              → Create lead
GET    /api/v1/leads/{id}         → Get lead
PUT    /api/v1/leads/{id}         → Update lead
DELETE /api/v1/leads/{id}         → Delete lead
GET    /api/v1/analytics          → List analytics events
POST   /api/v1/analytics          → Record event
GET    /api/v1/dashboard          → Dashboard stats
```

## Non-Functional Requirements

- Backend tests: 70%+ coverage
- Frontend: Responsive, Tailwind + pre-built UI components
- Docker: All services start with `docker compose up -d`
- No mock data — everything persisted to PostgreSQL
