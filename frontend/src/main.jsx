import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import Home from './pages/Home.jsx'
import Browse from './pages/Browse.jsx'
import Work from './pages/Work.jsx'
import Ask from './pages/Ask.jsx'
import Exhibitions from './pages/Exhibitions.jsx'
import Plan from './pages/Plan.jsx'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Home /> },
      { path: 'plan', element: <Plan /> },
      { path: 'exhibitions', element: <Exhibitions /> },
      { path: 'browse', element: <Browse /> },
      { path: 'work/:id', element: <Work /> },
      { path: 'ask', element: <Ask /> },
    ],
  },
])

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
