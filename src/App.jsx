import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'

// Estilos propios
import './style.css'

// Componentes de ejemplo para rutas protegidas y públicas
function Home() {
  return (
    <div className="container">
      <h1>Bienvenido a YERUZZA STUDIO</h1>
      <p>Esta es la página principal protegida.</p>
    </div>
  )
}

function Profile({ user }) {
  return (
    <div className="container">
      <h2>Perfil de usuario</h2>
      <p><strong>Usuario:</strong> {user?.username}</p>
      <p><strong>Rol:</strong> {user?.role}</p>
    </div>
  )
}

function NotFound() {
  return (
    <div className="container">
      <h2>404 - Página no encontrada</h2>
    </div>
  )
}

// Componente Login y Registro combinados
function AuthForm({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const toggleMode = () => {
    setError(null)
    setIsLogin(!isLogin)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register'
      const res = await fetch('/api' + endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Error en la autenticación')
      }
      const data = await res.json()
      if (data.access_token) {
        onLogin(data.access_token)
      } else {
        throw new Error('Token no recibido')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <h2>{isLogin ? 'Iniciar sesión' : 'Registrar cuenta'}</h2>
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Usuario:
          <input
            type="text"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoComplete="username"
            disabled={loading}
          />
        </label>
        <label>
          Contraseña:
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete={isLogin ? "current-password" : "new-password"}
            disabled={loading}
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Procesando...' : isLogin ? 'Entrar' : 'Registrar'}
        </button>
      </form>
      <button onClick={toggleMode} className="toggle-btn" disabled={loading}>
        {isLogin ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
      </button>
    </div>
  )
}

// Guardia de rutas protegidas
function PrivateRoute({ children, token }) {
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null)
  const [user, setUser] = useState(null)
  const [loadingUser, setLoadingUser] = useState(false)
  const navigate = useNavigate()

  // Guardar token en localStorage y estado
  const handleLogin = (newToken) => {
    localStorage.setItem('token', newToken)
    setToken(newToken)
    navigate('/')
  }

  // Cerrar sesión
  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    navigate('/login')
  }

  // Obtener datos del usuario con token
  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    const fetchUser = async () => {
      setLoadingUser(true)
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) {
          throw new Error('Token inválido o expirado')
        }
        const data = await res.json()
        setUser(data)
      } catch {
        handleLogout()
      } finally {
        setLoadingUser(false)
      }
    }
    fetchUser()
  }, [token])

  return (
    <Router>
      <div className="app">
        <header className="header">
          <h1>YERUZZA STUDIO</h1>
          {token && user && (
            <nav>
              <button onClick={handleLogout} className="btn-logout">Cerrar sesión</button>
            </nav>
          )}
        </header>

        <main>
          <Routes>
            <Route
              path="/"
              element={
                <PrivateRoute token={token}>
                  {loadingUser ? <p>Cargando usuario...</p> : <Home />}
                </PrivateRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <PrivateRoute token={token}>
                  {loadingUser ? <p>Cargando usuario...</p> : <Profile user={user} />}
                </PrivateRoute>
              }
            />
            <Route
              path="/login"
              element={token ? <Navigate to="/" replace /> : <AuthForm onLogin={handleLogin} />}
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>

        <footer className="footer">
          <p>© 2026 YERUZZA STUDIO</p>
        </footer>
      </div>
    </Router>
  )
}