import { NavLink } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <NavLink to="/" className="navbar-brand">
          News Summarizer
        </NavLink>

        <div className="navbar-links">
          <NavLink
            to="/"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            Dashboard
          </NavLink>

          <NavLink
            to="/articles"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            Articles
          </NavLink>

          <NavLink
            to="/trending"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            Trending
          </NavLink>

          <NavLink
            to="/compare"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            Compare
          </NavLink>

          <NavLink
            to="/chat"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            Chat
          </NavLink>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
