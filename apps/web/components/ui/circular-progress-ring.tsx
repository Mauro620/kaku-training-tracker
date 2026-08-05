type Props = {
  /** 0–100. Si null, renderiza guion. */
  valor: number | null;
  /** Diámetro en px. Default 96. */
  tamano?: number;
  /** Grosor del trazo en px. Default 8. */
  grosor?: number;
  /** Color del progreso (token del DESIGN.md). Default = focus (púrpura). */
  color?: string;
};

/**
 * Anillo de progreso de un solo trazo (DESIGN.md §3.1).
 * Pista en gris surface-secondary, progreso en el color elegido.
 * Número al centro en tipografía bold.
 */
export function CircularProgressRing({
  valor,
  tamano = 96,
  grosor = 8,
  color = "var(--state-focus)",
}: Props) {
  const radio = (tamano - grosor) / 2;
  const circunferencia = 2 * Math.PI * radio;
  const progreso = valor === null ? 0 : Math.max(0, Math.min(100, valor));
  const dashoffset = circunferencia - (progreso / 100) * circunferencia;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: tamano, height: tamano }}
    >
      <svg
        width={tamano}
        height={tamano}
        viewBox={`0 0 ${tamano} ${tamano}`}
        className="-rotate-90"
        aria-hidden
      >
        <circle
          cx={tamano / 2}
          cy={tamano / 2}
          r={radio}
          fill="none"
          stroke="var(--surface-secondary)"
          strokeWidth={grosor}
        />
        <circle
          cx={tamano / 2}
          cy={tamano / 2}
          r={radio}
          fill="none"
          stroke={color}
          strokeWidth={grosor}
          strokeLinecap="round"
          strokeDasharray={circunferencia}
          strokeDashoffset={dashoffset}
          style={{ transition: "stroke-dashoffset 250ms cubic-bezier(0.16, 1, 0.3, 1)" }}
        />
      </svg>
      <span
        className="absolute text-[24px] font-bold tabular text-text-primary"
        aria-label={valor === null ? "sin datos" : `${valor} sobre 100`}
      >
        {valor === null ? "—" : valor}
      </span>
    </div>
  );
}
