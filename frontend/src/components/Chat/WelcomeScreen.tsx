export function WelcomeScreen() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-600 text-3xl font-bold text-white shadow-lg">
        N
      </div>
      <h2 className="mb-2 text-2xl font-semibold text-[#ececf1]">
        How can I help you today?
      </h2>
      <p className="text-center text-[#8e8ea0] max-w-md">
        I'm the NUST Bank Assistant. Ask me about account services, funds transfer, mobile banking, and more.
      </p>
    </div>
  );
}
