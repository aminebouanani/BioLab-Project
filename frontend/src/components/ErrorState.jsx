export default function ErrorState({ message, onRetry }) {
  return (
    <div className="panel error-panel">
      <h3>Something needs attention</h3>
      <p>{message}</p>
      {onRetry && <button onClick={onRetry}>Try again</button>}
    </div>
  );
}
