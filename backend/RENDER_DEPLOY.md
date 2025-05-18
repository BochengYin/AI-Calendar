# Render Deployment Guide

This guide explains how to deploy the AI Calendar backend to Render.

## Step 1: Set up a new Web Service

1. Log in to your Render dashboard
2. Click "New" and select "Web Service"
3. Connect your GitHub repository
4. Select the repository and the branch you want to deploy
5. Use the following settings:
   - **Name**: ai-calendar-backend
   - **Environment**: Python
   - **Region**: Choose one close to your users
   - **Branch**: main (or your preferred branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Root Directory**: `backend` (IMPORTANT: make sure to set this to the backend subdirectory)

## Step 2: Add Environment Variables

Add the following environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `PORT`: 10000
- `DEBUG_ENDPOINTS`: true

## Step 3: Deploy

Click "Create Web Service" and wait for the deployment to complete.

## Step 4: Fix the API Health Check

If you continue to see 404 errors on `/api/health`, try these steps:

1. Check the Render logs to see if the server is starting properly
2. Verify that the service is using the correct root directory (`backend`)
3. Try accessing different URL formats:
   - `https://your-service.onrender.com/api/health`
   - `https://your-service.onrender.com/health`
   - `https://your-service.onrender.com/`

4. If needed, modify your CORS settings or add more verbose logging to troubleshoot the issue.

## Step 5: Update the Frontend

Make sure your frontend is configured to use the new backend URL:

```javascript
// In your frontend React app
const API_URL = "https://your-render-service-name.onrender.com";
``` 