export function Icon({ name, className = "" }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined app-icon ${className}`.trim()} aria-hidden="true">{name}</span>;
}

