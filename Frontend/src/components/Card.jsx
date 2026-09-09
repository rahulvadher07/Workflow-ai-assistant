export default function Card({ className = "", children, ...props }) {
  return (
    <div
      className={`surface-card p-5 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
