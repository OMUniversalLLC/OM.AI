/** Optional React link component for the EXISTING OM Universal dashboard.
 * Add this to a protected navigation section. The URL is not a credential.
 * The OM AI Apps Script app re-checks Google identity, Users allowlist and Sheets permissions.
 */
export default function OmAiLauncher() {
  const url = process.env.NEXT_PUBLIC_OM_AI_URL;
  if (!url) return null;
  if (!/^https:\/\/script\.google\.com\/macros\/s\//.test(url)) return null;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
       className="inline-flex items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
      ✦ Open OM AI Intelligence Center
    </a>
  );
}
