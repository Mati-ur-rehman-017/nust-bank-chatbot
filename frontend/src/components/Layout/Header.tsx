export function Header() {
  return (
    <header className="flex items-center gap-3 border-b border-[#4e4f60] bg-[#202123] px-6 py-3 text-white">
      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-600 text-white font-bold text-lg">
        N
      </div>
      <div>
        <h1 className="text-lg font-semibold leading-tight text-[#ececf1]">
          NUST Bank Assistant
        </h1>
        <p className="text-xs text-[#8e8ea0]">
          AI-powered customer support
        </p>
      </div>
    </header>
  );
}
