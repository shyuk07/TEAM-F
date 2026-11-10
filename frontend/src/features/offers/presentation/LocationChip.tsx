export type LocationChipProps = { label: string; open: boolean; onClick(): void };

export function LocationChip({ label, open, onClick }: LocationChipProps) {
  return (
    <button
      type="button"
      className={open ? 'chip on' : 'chip'}
      aria-haspopup="dialog"
      aria-expanded={open}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
