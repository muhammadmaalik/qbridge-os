export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="login-light-shell min-h-screen bg-[#f4f4f4] text-[#161616]">
      {children}
    </div>
  );
}
