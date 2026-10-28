import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

// Vite base is /sdoc-shipping-verification/ on GitHub Pages. Strip the trailing slash for the router.
const pagesBase = import.meta.env.BASE_URL.replace(/\/$/, '');
const basename = pagesBase && pagesBase !== '.' ? pagesBase : undefined;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
