import Spinner from "./Spinner";

export default function LoadingScreen() {
  return (
    <div className="flex h-full min-h-[240px] items-center justify-center">
      <Spinner className="h-6 w-6" />
    </div>
  );
}
