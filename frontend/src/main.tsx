import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

// Configure dayjs to use Portuguese (Brazil) locale
dayjs.locale('pt-br');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
