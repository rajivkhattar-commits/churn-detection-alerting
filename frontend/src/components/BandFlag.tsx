export function BandFlag({ label, bandKey }: { label: string; bandKey: string }) {
  return (
    <span className={`band-flag band-flag--${bandKey}`} title={label}>
      {label}
    </span>
  );
}
