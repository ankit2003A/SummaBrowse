# SummaBrowse: Free Hosting Deployment Guide

This guide will help you deploy your SummaBrowse app for free, with a live URL, using Render.com, Railway.app, or Fly.io. No credit card or payment required!

---

## 1. Prerequisites
- A free account on [GitHub](https://github.com/)
- A free account on [Render.com](https://render.com/), [Railway.app](https://railway.app/), or [Fly.io](https://fly.io/)
- Your project code pushed to a GitHub repository

---

## 2. Deploy on Render.com (Recommended for Simplicity)

1. **Push your code to GitHub.**
2. **Go to [Render.com](https://dashboard.render.com/)** and click "New +" → "Web Service".
3. **Connect your GitHub repo.**
4. **Select the Dockerfile option.**
5. **Set the build and start commands:**
   - Build Command: *(leave blank, Render uses Dockerfile)*
   - Start Command: *(leave blank, Render uses Dockerfile)*
6. **Set environment variables (optional):**
   - HOST=0.0.0.0
   - PORT=5000
7. **Expose port 5000.**
8. **Click "Create Web Service".**
9. Wait for the build and deploy to finish. Your live URL will be shown at the top of the service page (e.g., `https://your-app-name.onrender.com`).

---

## 3. Deploy on Railway.app

1. **Push your code to GitHub.**
2. **Go to [Railway.app](https://railway.app/)** and click "New Project" → "Deploy from GitHub repo".
3. **Select your repo and let Railway auto-detect the Dockerfile.**
4. **Set environment variables (optional):**
   - HOST=0.0.0.0
   - PORT=5000
5. **Deploy!**
6. Your live URL will be shown in the project dashboard (e.g., `https://your-app-name.up.railway.app`).

---

## 4. Deploy on Fly.io

1. **Install the [Fly.io CLI](https://fly.io/docs/hands-on/install-flyctl/).**
2. **Run `fly launch` in your project directory.**
3. **Follow the prompts (choose a name, region, etc.).**
4. **Deploy with `fly deploy`.**
5. Your live URL will be shown in the output (e.g., `https://your-app-name.fly.dev`).

---

## 5. Local Docker Test (Optional)

```sh
docker build -t summa-browse .
docker run -p 5000:5000 summa-browse
```
Visit [http://localhost:5000](http://localhost:5000) to test locally.

---

## 6. No Database or Auth Needed
- This app is stateless and file-based. No database or authentication is required for deployment.

---

## 7. Need Help?
- If you get stuck, check the platform’s documentation or ask for help!

---

**Enjoy your free, live SummaBrowse app!** 