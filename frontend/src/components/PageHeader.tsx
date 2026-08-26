import type { ReactNode } from "react";

export function PageHeader(props: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">{props.eyebrow}</span>
        <h1>{props.title}</h1>
        <p>{props.description}</p>
      </div>
      {props.action}
    </header>
  );
}
