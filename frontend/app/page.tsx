

"use client";



import { useEffect, useMemo, useState } from "react";



type Requirement = {

  requirement: string;

  possible_points?: number;

  earned_points?: number;

  evidence?: Evidence[];

};



type Evidence = {

  source?: string;

  text?: string;

  credit?: number;

};



type ApiCandidate = {

  filename: string;

  category: string;

  score: number;

  rank: number;

  matched_requirements: Requirement[];

  missing_requirements: string[];

  manual_review_required: boolean;

  classification_reason: string;

};
type ApiProfile = {
  filename: string;
  duplicate_group_id?: string | null;
  duplicate_status?: string;
  duplicate_of?: string | null;
  duplicate_reason?: string | null;
  duplicate_review_required?: boolean;
};



type Candidate = {

  id: string;

  role: string;

  score: number;

  rank: number;

  category: string;

  skills: string[];

  matched: Requirement[];

  missing: string[];

  evidence: Evidence[];

  review: boolean;

  reason: string;

};



type RankingResponse = {

  total_candidates: number;

  ranking_method: string;

  lca_ranking: ApiCandidate[];

  ui_ux_ranking: ApiCandidate[];

};



// const API_URL = "http://127.0.0.1:8000";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";



const navigation = [

  { label: "Overview", icon: "▦" },

  { label: "LCA Consultant", icon: "◈" },

  { label: "UI/UX Design", icon: "✳" },

  { label: "All Candidates", icon: "♙" },

  { label: "Upload Resumes", icon: "↑" },

  { label: "HR Review", icon: "✓" },

  { label: "Duplicate Review", icon: "⚠" }

];



function scoreColor(score: number) {

  if (score >= 70) return "text-emerald-700 bg-emerald-50";

  if (score >= 45) return "text-blue-700 bg-blue-50";

  return "text-amber-700 bg-amber-50";

}



function convertCandidates(

  items: ApiCandidate[],

  role: "LCA Consultant" | "UI/UX Design"

): Candidate[] {

  return items.map((item) => ({

    id: item.filename,

    role,

    score: Number(item.score) || 0,

    rank: item.rank,

    category: item.category || "Uncertain",

    skills: (item.matched_requirements || []).map(

      (requirement) => requirement.requirement

    ),

    matched: item.matched_requirements || [],

    missing: item.missing_requirements || [],

    evidence: (item.matched_requirements || []).flatMap(

      (requirement) => requirement.evidence || []

    ),

    review: Boolean(item.manual_review_required),

    reason: item.classification_reason || "",

  }));

}



export default function Home() {

  const [activePage, setActivePage] = useState("Overview");

  const [search, setSearch] = useState("");

  const [selectedCandidate, setSelectedCandidate] =

    useState<Candidate | null>(null);



  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [duplicateProfiles, setDuplicateProfiles] = useState<ApiProfile[]>([]);

  const [totalCandidates, setTotalCandidates] = useState(0);

  const [rankingMethod, setRankingMethod] = useState("");



  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const [uploading, setUploading] = useState(false);

  const [uploadMessage, setUploadMessage] = useState("");

  const [uploadError, setUploadError] = useState("");

  const [uploadResult, setUploadResult] = useState<{

    uploaded?: number;

    new_candidates?: number;

    total_candidates?: number;

    classification_counts?: Record<string, number>;

    results?: Array<{ filename: string; status: string; message: string }>;

  } | null>(null);



  // Fetch real ranking data from FastAPI

  useEffect(() => {

    async function fetchRankings() {

      try {

        setLoading(true);

        setError("");



        const response = await fetch(`${API_URL}/api/rankings`);



        if (!response.ok) {

          throw new Error(`Backend returned ${response.status}`);

        }



        const data: RankingResponse = await response.json();



        if (

          !Array.isArray(data.lca_ranking) ||

          !Array.isArray(data.ui_ux_ranking)

        ) {

          throw new Error("Ranking data has an unexpected format.");

        }



        const lcaCandidates = convertCandidates(

          data.lca_ranking,

          "LCA Consultant"

        );



        const uiuxCandidates = convertCandidates(

          data.ui_ux_ranking,

          "UI/UX Design"

        );



        setCandidates([...lcaCandidates, ...uiuxCandidates]);

        setTotalCandidates(data.total_candidates || 0);

        setRankingMethod(data.ranking_method || "");
        const profilesResponse = await fetch(`${API_URL}/api/profiles`);

        if (!profilesResponse.ok) {
        throw new Error("Unable to load candidate profiles.");
      }

      const profilesData: ApiProfile[] = await profilesResponse.json();

      if (!Array.isArray(profilesData)) {
        throw new Error("Profile data has an unexpected format.");
     }

      setDuplicateProfiles(
      profilesData.filter(
        (profile) =>
          profile.duplicate_review_required ||
          profile.duplicate_status === "duplicate" ||
          profile.duplicate_status === "primary"
      )
      );

      } catch (err) {

        console.error("Ranking API error:", err);

        setError(

          "Unable to load candidate rankings. Make sure your FastAPI backend is running at http://127.0.0.1:8000."

        );

      } finally {

        setLoading(false);

      }

    }



    fetchRankings();

  }, []);



  async function handleUpload() {

    if (selectedFiles.length === 0) {

      setUploadError("Please select at least one PDF or DOCX resume.");

      setUploadMessage("");

      return;

    }



    setUploading(true);

    setUploadError("");

    setUploadMessage("");

    setUploadResult(null);



    try {

      const formData = new FormData();

      selectedFiles.forEach((file) => formData.append("files", file));



      const response = await fetch(`${API_URL}/api/upload`, {

        method: "POST",

        body: formData,

      });



      const result = await response.json();



      if (!response.ok) {

        const detail = typeof result.detail === "string"

          ? result.detail

          : JSON.stringify(result.detail || result);

        throw new Error(detail || `Upload failed with status ${response.status}`);

      }



      setUploadResult(result);

      setUploadMessage(result.message || "Upload and screening completed.");

      setSelectedFiles([]);



      // Refresh rankings so newly processed resumes appear in the dashboard.

      const rankingResponse = await fetch(`${API_URL}/api/rankings`);

      if (!rankingResponse.ok) {

        throw new Error("Resumes were uploaded, but the dashboard could not refresh. Please refresh the page.");

      }



      const rankingData: RankingResponse = await rankingResponse.json();

      if (!Array.isArray(rankingData.lca_ranking) || !Array.isArray(rankingData.ui_ux_ranking)) {

        throw new Error("Upload succeeded, but the refreshed ranking response has an unexpected format.");

      }



      const lcaCandidates = convertCandidates(rankingData.lca_ranking, "LCA Consultant");

      const uiuxCandidates = convertCandidates(rankingData.ui_ux_ranking, "UI/UX Design");

      setCandidates([...lcaCandidates, ...uiuxCandidates]);

      setTotalCandidates(rankingData.total_candidates || result.total_candidates || 0);

      setRankingMethod(rankingData.ranking_method || "");
      const profilesResponse = await fetch(`${API_URL}/api/profiles`);

      if (!profilesResponse.ok) {
          throw new Error("Resumes uploaded, but duplicate profiles could not be refreshed.");
      }

        const profilesData: ApiProfile[] = await profilesResponse.json();

      if (!Array.isArray(profilesData)) {
          throw new Error("Profile data has an unexpected format.");
      }

      setDuplicateProfiles(
        profilesData.filter(
        (profile) =>
          profile.duplicate_review_required ||
          profile.duplicate_status === "duplicate" ||
          profile.duplicate_status === "primary"
        )
      );

    } catch (err) {

      console.error("Resume upload error:", err);

      setUploadError(err instanceof Error ? err.message : "An unexpected upload error occurred.");

    } finally {

      setUploading(false);

    }

  }



  // Use one record per resume to calculate classification statistics

  const uniqueCandidates = useMemo(() => {

    const unique = new Map<string, Candidate>();



    candidates.forEach((candidate) => {

      if (!unique.has(candidate.id)) {

        unique.set(candidate.id, candidate);

      }

    });



    return Array.from(unique.values());

  }, [candidates]);



  const lcaCount = uniqueCandidates.filter(

    (candidate) => candidate.category === "LCA"

  ).length;



  const uiuxCount = uniqueCandidates.filter(

    (candidate) =>

      candidate.category === "UI/UX" ||

      candidate.category === "UI/UX Design"

  ).length;



  const bothCount = uniqueCandidates.filter(

    (candidate) => candidate.category === "Both"

  ).length;



  const uncertainCount = uniqueCandidates.filter(

    (candidate) =>

      candidate.category.toLowerCase().includes("uncertain") ||

      candidate.category.toLowerCase().includes("neither")

  ).length;



  const reviewCount = uniqueCandidates.filter(

    (candidate) => candidate.review

  ).length;



  // Filter candidates according to the selected page

  const filteredCandidates = useMemo(() => {

    let result = candidates;



    if (activePage === "LCA Consultant") {
      // Show only candidates actually classified for LCA (or Both).
      result = result.filter(
        (candidate) =>
          candidate.role === "LCA Consultant" &&
          (candidate.category === "LCA" || candidate.category === "Both") &&
          candidate.score > 0
      );
    } else if (activePage === "UI/UX Design") {
      // Show only candidates actually classified for UI/UX (or Both).
      result = result.filter(
        (candidate) =>
          candidate.role === "UI/UX Design" &&
          ["UI/UX", "UI/UX Design", "Both"].includes(candidate.category) &&
          candidate.score > 0
      );
    } else if (activePage === "All Candidates") {
      // One row per resume, labelled with its real classification category.
      result = uniqueCandidates.map((candidate) => ({
        ...candidate,
        role: candidate.category || "Neither / Uncertain",
      }));
    } else if (activePage === "HR Review") {
      // Avoid showing the same resume twice when it exists in both role rankings.
      result = uniqueCandidates
        .filter((candidate) => candidate.review)
        .map((candidate) => ({
          ...candidate,
          role: candidate.category || "Neither / Uncertain",
        }));
    }

    return result.filter((candidate) =>

      candidate.id.toLowerCase().includes(search.toLowerCase())

    );

  }, [activePage, search, candidates, uniqueCandidates]);



  const showCandidates =

    activePage === "LCA Consultant" ||

    activePage === "UI/UX Design" ||

    activePage === "All Candidates" ||

    activePage === "HR Review";



  function changePage(page: string) {

    setActivePage(page);

    setSearch("");

    setSelectedCandidate(null);

  }



  // Loading screen

  if (loading) {

    return (

      <div className="flex min-h-screen items-center justify-center bg-slate-50">

        <div className="text-center">

          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />

          <p className="mt-4 font-medium text-slate-700">

            Loading candidate rankings...

          </p>

          <p className="mt-1 text-sm text-slate-500">

            Connecting to TalentRank-AI backend

          </p>

        </div>

      </div>

    );

  }



  // Error screen

  if (error) {

    return (

      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">

        <div className="max-w-lg rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm">

          <div className="text-4xl text-red-500">!</div>

          <h2 className="mt-3 text-xl font-bold text-slate-900">

            Backend connection failed

          </h2>

          <p className="mt-3 text-sm leading-6 text-slate-600">

            {error}

          </p>

          <button

            onClick={() => window.location.reload()}

            className="mt-5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"

          >

            Try again

          </button>

        </div>

      </div>

    );

  }



  return (

    <div className="min-h-screen bg-slate-50 text-slate-900 md:flex">



      {/* Sidebar */}

      <aside className="w-full border-b border-slate-200 bg-white md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col md:border-b-0 md:border-r">



        <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-6">

          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-xl font-bold text-white">

            T

          </div>



          <div>

            <h1 className="text-lg font-bold tracking-tight">

              TalentRank<span className="text-indigo-600">AI</span>

            </h1>

            <p className="text-xs text-slate-500">

              Intelligent recruitment

            </p>

          </div>

        </div>



        <div className="px-4 py-5">

          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">

            Workspace

          </p>



          <nav className="flex gap-1 overflow-x-auto md:flex-col">

            {navigation.map((item) => (

              <button

                key={item.label}

                onClick={() => changePage(item.label)}

                className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium transition ${

                  activePage === item.label

                    ? "bg-indigo-50 text-indigo-700"

                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"

                }`}

              >

                <span className="w-5 text-center text-lg">

                  {item.icon}

                </span>

                {item.label}

              </button>

            ))}

          </nav>

        </div>



        <div className="mt-auto hidden border-t border-slate-100 p-5 md:block">

          <div className="rounded-xl bg-slate-50 p-4">

            <p className="text-sm font-semibold">

              Human-led decisions

            </p>

            <p className="mt-1 text-xs leading-5 text-slate-500">

              AI assists screening. Final hiring decisions remain with HR.

            </p>

          </div>

        </div>

      </aside>



      {/* Main content */}

      <main className="min-w-0 flex-1 md:ml-64">



        {/* Header */}

        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-5 lg:px-9">

          <div>

            <p className="text-sm text-slate-500">

              Recruitment workspace / {activePage}

            </p>

            <h2 className="mt-1 text-xl font-bold">

              {activePage}

            </h2>

          </div>



          <div className="flex items-center gap-3">

            <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">

              ● Backend connected

            </span>



            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700">

              HR

            </div>

          </div>

        </header>



        <div className="mx-auto max-w-7xl space-y-7 p-6 lg:p-9">



          {/* Overview */}

          {activePage === "Overview" && (

            <>

              <section>

                <p className="text-sm text-slate-500">

                  Welcome to TalentRank-AI

                </p>



                <h3 className="mt-1 text-2xl font-bold tracking-tight">

                  Candidate screening overview

                </h3>



                <p className="mt-2 text-sm text-slate-500">

                  Review actual candidate classifications and role-specific ranking results.

                </p>

              </section>



              {/* Statistics */}

              <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

                {[

                  {

                    label: "Total candidates",

                    value: totalCandidates,

                    note: "Resumes processed",

                    icon: "♙",

                  },

                  {

                    label: "LCA candidates",

                    value: lcaCount,

                    note: "Classified for LCA",

                    icon: "◈",

                  },

                  {

                    label: "UI/UX candidates",

                    value: uiuxCount,

                    note: "Classified for UI/UX",

                    icon: "✳",

                  },

                  {

                    label: "Manual reviews",

                    value: reviewCount,

                    note: "Require HR attention",

                    icon: "✓",

                  },

                ].map((card) => (

                  <div

                    key={card.label}

                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"

                  >

                    <div className="flex items-center justify-between">

                      <p className="text-sm font-medium text-slate-500">

                        {card.label}

                      </p>

                      <span className="text-xl text-indigo-600">

                        {card.icon}

                      </span>

                    </div>



                    <p className="mt-4 text-3xl font-bold">

                      {card.value}

                    </p>



                    <p className="mt-1 text-xs text-slate-400">

                      {card.note}

                    </p>

                  </div>

                ))}

              </section>



              {/* Role rankings */}

              <section className="grid gap-5 lg:grid-cols-2">



                {/* LCA */}

                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

                  <div className="flex items-center justify-between">

                    <div>

                      <h4 className="font-semibold">

                        LCA Consultant

                      </h4>

                      <p className="mt-1 text-xs text-slate-500">

                        Top-ranked candidates

                      </p>

                    </div>



                    <button

                      onClick={() => changePage("LCA Consultant")}

                      className="text-sm font-medium text-indigo-600 hover:underline"

                    >

                      View all →

                    </button>

                  </div>



                  <div className="mt-5 space-y-4">

                    {candidates

                      .filter(

                        (candidate) =>

                          candidate.role === "LCA Consultant" &&

                          candidate.score > 0

                      )

                      .slice(0, 3)

                      .map((candidate, index) => (

                        <div

                          key={candidate.id}

                          className="flex items-center gap-3"

                        >

                          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-sm font-semibold text-slate-600">

                            {index + 1}

                          </span>



                          <div className="min-w-0 flex-1">

                            <p className="truncate text-sm font-medium">

                              {candidate.id}

                            </p>

                            <p className="text-xs text-slate-400">

                              {candidate.skills.slice(0, 2).join(" · ")}

                            </p>

                          </div>



                          <span className="text-sm font-bold">

                            {candidate.score.toFixed(2)}%

                          </span>

                        </div>

                      ))}

                  </div>

                </div>



                {/* UI/UX */}

                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

                  <div className="flex items-center justify-between">

                    <div>

                      <h4 className="font-semibold">

                        UI/UX Design

                      </h4>

                      <p className="mt-1 text-xs text-slate-500">

                        Top-ranked candidates

                      </p>

                    </div>



                    <button

                      onClick={() => changePage("UI/UX Design")}

                      className="text-sm font-medium text-indigo-600 hover:underline"

                    >

                      View all →

                    </button>

                  </div>



                  <div className="mt-5 space-y-4">

                    {candidates

                      .filter(

                        (candidate) =>

                          candidate.role === "UI/UX Design" &&

                          candidate.score > 0

                      )

                      .slice(0, 3)

                      .map((candidate, index) => (

                        <div

                          key={candidate.id}

                          className="flex items-center gap-3"

                        >

                          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-sm font-semibold text-slate-600">

                            {index + 1}

                          </span>



                          <div className="min-w-0 flex-1">

                            <p className="truncate text-sm font-medium">

                              {candidate.id}

                            </p>

                            <p className="text-xs text-slate-400">

                              {candidate.skills.slice(0, 2).join(" · ")}

                            </p>

                          </div>



                          <span className="text-sm font-bold">

                            {candidate.score.toFixed(2)}%

                          </span>

                        </div>

                      ))}

                  </div>

                </div>

              </section>



              {/* Classification summary */}

              <section className="rounded-2xl border border-slate-200 bg-white p-5">

                <h4 className="font-semibold">

                  Classification summary

                </h4>



                <div className="mt-4 grid gap-4 sm:grid-cols-3">

                  <div>

                    <p className="text-2xl font-bold">{bothCount}</p>

                    <p className="text-xs text-slate-500">Both roles</p>

                  </div>



                  <div>

                    <p className="text-2xl font-bold">{uncertainCount}</p>

                    <p className="text-xs text-slate-500">

                      Neither / uncertain

                    </p>

                  </div>



                  <div>

                    <p className="text-2xl font-bold">{reviewCount}</p>

                    <p className="text-xs text-slate-500">

                      Require manual review

                    </p>

                  </div>

                </div>

              </section>



              {/* Important notice */}

              <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">

                <div className="flex gap-3">

                  <span className="text-xl">ⓘ</span>



                  <div>

                    <h4 className="text-sm font-semibold text-amber-900">

                      Important: Human review required

                    </h4>



                    <p className="mt-1 text-sm leading-6 text-amber-800">

                      Matching scores are preliminary, evidence-based decision-support estimates, not validated hiring assessments. They do not establish candidate suitability or automatically reject applicants. HR should verify qualifications and project experience.

                    </p>



                    {rankingMethod && (

                      <p className="mt-2 text-xs text-amber-800">

                        Ranking method: {rankingMethod}

                      </p>

                    )}

                  </div>

                </div>

              </section>

            </>

          )}



          {/* Candidate rankings */}

{/* Duplicate Review */}
{activePage === "Duplicate Review" && (
  <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
    <div className="border-b border-slate-100 p-5">
      <h3 className="font-semibold">Duplicate Resume Review</h3>
      <p className="mt-1 text-xs text-slate-500">
        Review resumes identified as possible duplicates. Verify each group
        manually before making any hiring decision.
      </p>

      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search filename or duplicate group..."
        className="mt-4 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
      />
    </div>

    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-5 py-4 font-semibold">Resume</th>
            <th className="px-5 py-4 font-semibold">Status</th>
            <th className="px-5 py-4 font-semibold">Duplicate Group</th>
            <th className="px-5 py-4 font-semibold">Duplicate Of</th>
            <th className="px-5 py-4 font-semibold">Reason</th>
            <th className="px-5 py-4 font-semibold">HR Review</th>
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100">
          {duplicateProfiles
            .filter((profile) =>
              [
                profile.filename,
                profile.duplicate_group_id || "",
                profile.duplicate_reason || "",
              ]
                .join(" ")
                .toLowerCase()
                .includes(search.toLowerCase())
            )
            .map((profile) => (
              <tr key={profile.filename} className="hover:bg-slate-50">
                <td className="max-w-64 break-all px-5 py-4 font-medium">
                  {profile.filename}
                </td>

                <td className="px-5 py-4">
                  <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                    {profile.duplicate_status || "Needs review"}
                  </span>
                </td>

                <td className="px-5 py-4 text-slate-600">
                  {profile.duplicate_group_id || "—"}
                </td>

                <td className="max-w-48 break-all px-5 py-4 text-slate-600">
                  {profile.duplicate_of || "—"}
                </td>

                <td className="min-w-56 px-5 py-4 text-slate-600">
                  {profile.duplicate_reason || "No reason provided"}
                </td>

                <td className="px-5 py-4">
                  <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                    {profile.duplicate_review_required
                      ? "Review required"
                      : "Check manually"}
                  </span>
                </td>
              </tr>
            ))}

          {duplicateProfiles.filter((profile) =>
            [
              profile.filename,
              profile.duplicate_group_id || "",
              profile.duplicate_reason || "",
            ]
              .join(" ")
              .toLowerCase()
              .includes(search.toLowerCase())
          ).length === 0 && (
            <tr>
              <td
                colSpan={6}
                className="px-5 py-12 text-center text-slate-500"
              >
                No duplicate profiles found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  </section>
)}


          {showCandidates && (

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">



              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5">

                <div>

                  <h3 className="font-semibold">

                    Candidate rankings

                  </h3>



                  <p className="mt-1 text-xs text-slate-500">

                    {filteredCandidates.length} displayed records · Ranked by role-specific score

                  </p>

                </div>



                <input

                  value={search}

                  onChange={(event) => setSearch(event.target.value)}

                  placeholder="Search candidate ID..."

                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 sm:w-72"

                />

              </div>



              <div className="overflow-x-auto">

                <table className="w-full text-left text-sm">

                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">

                    <tr>

                      <th className="px-5 py-4 font-semibold">Rank</th>

                      <th className="px-5 py-4 font-semibold">Candidate</th>

                      <th className="px-5 py-4 font-semibold">Role</th>

                      <th className="px-5 py-4 font-semibold">Matched requirements</th>

                      <th className="px-5 py-4 font-semibold">Score</th>

                      <th className="px-5 py-4 font-semibold">HR status</th>

                      <th className="px-5 py-4 font-semibold">Details</th>

                    </tr>

                  </thead>



                  <tbody className="divide-y divide-slate-100">

                    {filteredCandidates.map((candidate) => (

                      <tr

                        key={`${candidate.role}-${candidate.id}`}

                        className="hover:bg-slate-50"

                      >

                        <td className="px-5 py-4 font-semibold text-slate-500">

                          {activePage === "All Candidates" || activePage === "HR Review"
                            ? "—"
                            : candidate.rank}

                        </td>



                        <td className="max-w-64 truncate px-5 py-4 font-medium">

                          {candidate.id}

                        </td>



                        <td className="whitespace-nowrap px-5 py-4 text-slate-600">

                          {candidate.role}

                        </td>



                        <td className="min-w-48 px-5 py-4">

                          <div className="flex flex-wrap gap-1">

                            {candidate.skills.slice(0, 4).map((skill) => (

                              <span

                                key={skill}

                                className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600"

                              >

                                {skill}

                              </span>

                            ))}



                            {candidate.skills.length > 4 && (

                              <span className="text-xs text-slate-400">

                                +{candidate.skills.length - 4} more

                              </span>

                            )}



                            {candidate.skills.length === 0 && (

                              <span className="text-xs text-slate-400">

                                No matched requirements

                              </span>

                            )}

                          </div>

                        </td>



                        <td className="px-5 py-4">

                          <span

                            className={`rounded-lg px-2.5 py-1.5 text-xs font-bold ${scoreColor(candidate.score)}`}

                          >

                            {candidate.score.toFixed(2)}%

                          </span>

                        </td>



                        <td className="whitespace-nowrap px-5 py-4">

                          <span

                            className={`rounded-full px-2.5 py-1 text-xs font-medium ${

                              candidate.review

                                ? "bg-amber-50 text-amber-700"

                                : "bg-emerald-50 text-emerald-700"

                            }`}

                          >

                            {candidate.review

                              ? "Review required"

                              : "Flag not set"}

                          </span>

                        </td>



                        <td className="px-5 py-4">

                          <button
                            type="button"
                            onClick={() => setSelectedCandidate(candidate)}
                            className="rounded-md bg-indigo-50 px-3 py-1.5 font-medium text-indigo-700 hover:bg-indigo-100"
                          >
                            View Details
                          </button>

                        </td>

                      </tr>

                    ))}



                    {filteredCandidates.length === 0 && (

                      <tr>

                        <td

                          colSpan={7}

                          className="px-5 py-12 text-center text-slate-500"

                        >

                          No matching candidates found.

                        </td>

                      </tr>

                    )}

                  </tbody>

                </table>

              </div>

            </section>

          )}



          {/* Resume upload */}

          {activePage === "Upload Resumes" && (

            <section className="mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">

              <div className="text-center">

                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl text-indigo-600">

                  ↑

                </div>

                <h3 className="mt-4 text-xl font-semibold">Upload new resumes</h3>

                <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">

                  Select one or more PDF or DOCX resumes. TalentRank-AI will extract the text, create candidate profiles, classify them, and refresh the rankings.

                </p>

              </div>



              <div className="mt-7 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-6">

                <label htmlFor="resume-files" className="block text-sm font-semibold text-slate-700">

                  Choose resume files

                </label>

                <input

                  id="resume-files"

                  type="file"

                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                  multiple

                  disabled={uploading}

                  onChange={(event) => {

                    setSelectedFiles(Array.from(event.target.files || []));

                    setUploadError("");

                    setUploadMessage("");

                    setUploadResult(null);

                  }}

                  className="mt-3 block w-full cursor-pointer rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-indigo-700 hover:file:bg-indigo-100"

                />

                <p className="mt-2 text-xs text-slate-500">Accepted formats: PDF and DOCX. The backend enforces file size and upload-count limits.</p>

                {selectedFiles.length > 0 && (

                  <div className="mt-4 rounded-lg bg-white p-3">

                    <p className="text-sm font-semibold text-slate-700">{selectedFiles.length} file(s) selected</p>

                    <ul className="mt-2 space-y-1 text-xs text-slate-600">

                      {selectedFiles.map((file, index) => (

                        <li key={`${file.name}-${index}`} className="break-all">• {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</li>

                      ))}

                    </ul>

                  </div>

                )}

              </div>



              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">

                <p className="text-xs text-slate-500">Existing candidates are retained when new resumes are added.</p>

                <button

                  type="button"

                  onClick={handleUpload}

                  disabled={uploading || selectedFiles.length === 0}

                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"

                >

                  {uploading ? "Uploading and screening..." : "Upload and screen resumes"}

                </button>

              </div>



              {uploading && (

                <div className="mt-5 rounded-lg bg-indigo-50 p-4 text-sm text-indigo-800">

                  Processing resumes. Please keep this page open until the operation finishes.

                </div>

              )}



              {uploadError && (

                <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">

                  {uploadError}

                </div>

              )}



              {uploadMessage && (

                <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4">

                  <p className="text-sm font-semibold text-emerald-800">{uploadMessage}</p>

                  {uploadResult && (

                    <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">

                      <div><p className="text-xs text-emerald-700">Uploaded</p><p className="text-xl font-bold text-emerald-900">{uploadResult.uploaded ?? 0}</p></div>

                      <div><p className="text-xs text-emerald-700">New candidates</p><p className="text-xl font-bold text-emerald-900">{uploadResult.new_candidates ?? 0}</p></div>

                      <div><p className="text-xs text-emerald-700">Total candidates</p><p className="text-xl font-bold text-emerald-900">{uploadResult.total_candidates ?? totalCandidates}</p></div>

                    </div>

                  )}

                  {uploadResult?.results && (

                    <ul className="mt-3 space-y-2 text-xs text-emerald-900">

                      {uploadResult.results.map((item, index) => (

                        <li key={`${item.filename}-${index}`} className="rounded-md bg-white/70 p-2">

                          <span className="font-semibold">{item.filename}</span> — {item.status}: {item.message}

                        </li>

                      ))}

                    </ul>

                  )}

                  <p className="mt-3 text-xs text-emerald-800">The candidate rankings and dashboard statistics have been refreshed.</p>

                </div>

              )}

            </section>

          )}



                    {/* Candidate details modal */}
          {selectedCandidate && (
            <div
              className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 p-4"
              onClick={() => setSelectedCandidate(null)}
            >
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="candidate-modal-title"
                onClick={(event) => event.stopPropagation()}
                className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl"
              >
                <div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">Candidate profile</p>
                    <h3 id="candidate-modal-title" className="mt-2 break-all text-lg font-bold text-slate-900">
                      {selectedCandidate.id}
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">{selectedCandidate.role}</p>
                  </div>
                  <button type="button" onClick={() => setSelectedCandidate(null)} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium hover:bg-slate-50">
                    ✕ Close
                  </button>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-4">
                  <div className="rounded-xl bg-indigo-50 p-4">
                    <p className="text-xs text-slate-500">Matching score</p>
                    <p className="mt-1 text-2xl font-bold text-indigo-700">{selectedCandidate.score.toFixed(2)}%</p>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Ranking position</p>
                    <p className="mt-1 text-2xl font-bold text-slate-900">#{selectedCandidate.rank}</p>
                  </div>
                </div>

                <section className="mt-6">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="font-semibold text-slate-900">Matched requirements and resume evidence</h4>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                      {selectedCandidate.matched.length} matched
                    </span>
                  </div>
                  <div className="mt-3 space-y-3">
                    {selectedCandidate.matched.length > 0 ? selectedCandidate.matched.map((requirement) => (
                      <div key={requirement.requirement} className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
                        <div className="flex flex-wrap justify-between gap-2">
                          <p className="font-semibold text-slate-800">{requirement.requirement}</p>
                          <span className="text-xs text-emerald-700">{requirement.earned_points ?? 0}/{requirement.possible_points ?? 0} points</span>
                        </div>
                        {requirement.evidence?.length ? requirement.evidence.map((item, index) => (
                          <div key={`${requirement.requirement}-${index}`} className="mt-3 border-l-2 border-emerald-300 pl-3">
                            <p className="text-xs font-medium text-slate-500">Source: {item.source || "Resume"}</p>
                            <p className="mt-1 text-sm leading-6 text-slate-700">{item.text || "No evidence text available."}</p>
                          </div>
                        )) : <p className="mt-2 text-sm text-slate-500">No supporting evidence recorded.</p>}
                      </div>
                    )) : <p className="text-sm text-slate-500">No matched requirements recorded.</p>}
                  </div>
                </section>

                <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50/40 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h4 className="font-semibold text-slate-900">Requirements not matched</h4>
                      <p className="mt-1 text-xs text-slate-500">
                        These are requirements for which the current resume analysis did not find sufficient evidence.
                      </p>
                    </div>
                    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                      {selectedCandidate.missing.length} to verify
                    </span>
                  </div>

                  {selectedCandidate.missing.length > 0 ? (
                    <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                      {selectedCandidate.missing.map((item, index) => (
                        <li
                          key={`${item}-${index}`}
                          className="flex items-start gap-2 rounded-lg border border-amber-100 bg-white px-3 py-2.5 text-sm text-amber-900"
                        >
                          <span className="mt-0.5 text-amber-600">•</span>
                          <span className="break-words">{String(item).replace(/^[\s•-]+/, "")}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-4 rounded-lg bg-white px-3 py-3 text-sm text-slate-600">
                      No unmatched requirements were recorded by the current analysis.
                    </p>
                  )}
                </section>

                <section className="mt-6 rounded-xl bg-slate-50 p-4">
                  <h4 className="font-semibold text-slate-900">Classification reason</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{selectedCandidate.reason || "No classification reason provided."}</p>
                </section>

                <section className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <h4 className="font-semibold text-amber-900">HR verification</h4>
                  <p className="mt-2 text-sm leading-6 text-amber-800">
                    {selectedCandidate.review
                      ? "Manual review is required. Verify the original resume and supporting qualifications."
                      : "No manual-review flag was set. HR should still verify the original resume."}
                  </p>
                </section>

                <div className="mt-6 flex justify-end">
                  <button type="button" onClick={() => setSelectedCandidate(null)} className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">Close profile</button>
                </div>
              </div>
            </div>
          )}

          {/* Footer */}

          <footer className="border-t border-slate-200 pt-5 text-xs text-slate-400">

            TalentRank-AI · Resume screening and decision support · Human review remains essential

          </footer>

        </div>

      </main>

    </div>

  );

}
