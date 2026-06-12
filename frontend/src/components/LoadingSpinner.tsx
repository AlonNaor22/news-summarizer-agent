import { strings } from '../strings';
import './LoadingSpinner.css';

interface Props {
  size?: 'small' | 'medium' | 'large';
  message?: string;
}

function LoadingSpinner({ size = 'medium', message = strings.common.loading }: Props) {
  return (
    <div className="loading-container">
      <div className={`spinner ${size}`}></div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
}

export default LoadingSpinner;
