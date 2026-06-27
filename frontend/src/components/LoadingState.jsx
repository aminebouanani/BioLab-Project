export default function LoadingState({ message = "Loading..." }) {
  return (
    <div className="panel muted-panel">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  );
}
