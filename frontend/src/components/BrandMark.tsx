import Image from 'next/image';

interface BrandMarkProps {
  size?: number;
}

// NextHire arrow-icon brand mark (transparent PNG in /public).
export default function BrandMark({ size = 40 }: BrandMarkProps) {
  return (
    <Image
      src="/nexthire-icon.png"
      alt="NextHire logo"
      width={size}
      height={size}
      className="shrink-0 object-contain"
      priority
    />
  );
}
