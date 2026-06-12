import { NavLink } from 'react-router-dom';
import { strings } from '../strings';
import './Navbar.css';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <NavLink to="/" className="navbar-brand">
          {strings.nav.brand}
        </NavLink>

        <div className="navbar-links">
          <NavLink
            to="/"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            {strings.nav.dashboard}
          </NavLink>

          <NavLink
            to="/articles"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            {strings.nav.articles}
          </NavLink>

          <NavLink
            to="/trending"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            {strings.nav.trending}
          </NavLink>

          <NavLink
            to="/compare"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            {strings.nav.compare}
          </NavLink>

          <NavLink
            to="/chat"
            className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
          >
            {strings.nav.chat}
          </NavLink>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
