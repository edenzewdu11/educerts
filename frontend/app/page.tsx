"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Upload, FileText, CheckCircle, Shield, Search, Download } from "lucide-react"
import axios from "axios"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"

export default function Home() {
  const [activeTab, setActiveTab] = useState("login")
  const [isLogin, setIsLogin] = useState(true)
  const [authData, setAuthData] = useState({ name: "", email: "", password: "" })
  const [user, setUser] = useState<any>(null)
  const [file, setFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState("")
  const [certificates, setCertificates] = useState<any[]>([])
  const [verifyId, setVerifyId] = useState("")
  const [verifyResult, setVerifyResult] = useState<any>(null)

  const handleAuth = async () => {
    try {
      if (isLogin) {
        const params = new URLSearchParams();
        params.append('username', authData.name);
        params.append('password', authData.password);

        const res = await axios.post("http://localhost:8000/api/login", params);
        localStorage.setItem("token", res.data.access_token);
        setUser(res.data.user);
        setActiveTab(res.data.user.is_admin ? "admin" : "student");
      } else {
        await axios.post("http://localhost:8000/api/signup", {
          name: authData.name,
          email: authData.email,
          password: authData.password
        });
        setIsLogin(true);
        setUploadStatus("Registration successful! Please login.");
      }
    } catch (error: any) {
      const errorData = error.response?.data?.detail;
      if (typeof errorData === 'string') {
        setUploadStatus(errorData);
      } else if (Array.isArray(errorData)) {
        // Handle FastAPI validation error list
        setUploadStatus(errorData[0]?.msg || "Validation error");
      } else if (typeof errorData === 'object' && errorData !== null) {
        setUploadStatus(JSON.stringify(errorData));
      } else {
        setUploadStatus("Authentication error");
      }
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0])
    }
  }

  const handleImport = async () => {
    if (!file) return
    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await axios.post("http://localhost:8000/api/import", formData)
      setUploadStatus(`Success: ${res.data.count} records imported.`)
      // Trigger issuance for demo purposes (usually separate step)
      for (const record of res.data.data) {
        await axios.post("http://localhost:8000/api/issue", {
          student_name: record.student_name,
          course_name: record.course_name,
          data_payload: record
        })
      }
      setUploadStatus(prev => prev + " Certificates issued!")
    } catch (error) {
      setUploadStatus("Error uploading file.")
    }
  }

  const handleVerify = async () => {
    try {
      const res = await axios.post("http://localhost:8000/api/verify", {
        certificate_id: verifyId
      })
      setVerifyResult(res.data)
    } catch (error) {
      setVerifyResult({ valid: false, reason: "Certificate not found or invalid" })
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 font-sans selection:bg-indigo-500/30">
      <nav className="border-b border-slate-800 bg-slate-950/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
            <Shield className="w-6 h-6 text-indigo-500" />
            <span>EduCerts<span className="text-indigo-500">.io</span></span>
          </div>
          <div className="flex gap-4 text-sm font-medium text-slate-400">
            {user ? (
              <>
                {user.is_admin && <button onClick={() => setActiveTab("admin")} className={`hover:text-white transition-colors ${activeTab === "admin" ? "text-indigo-400" : ""}`}>Admin</button>}
                <button onClick={() => setActiveTab("student")} className={`hover:text-white transition-colors ${activeTab === "student" ? "text-indigo-400" : ""}`}>My Certificates</button>
                <button onClick={() => { setUser(null); setActiveTab("login"); localStorage.removeItem("token"); }} className="hover:text-white transition-colors">Logout</button>
              </>
            ) : (
              <button onClick={() => setActiveTab("login")} className={`hover:text-white transition-colors ${activeTab === "login" ? "text-indigo-400" : ""}`}>Login</button>
            )}
            <button onClick={() => setActiveTab("verifier")} className={`hover:text-white transition-colors ${activeTab === "verifier" ? "text-indigo-400" : ""}`}>Verifier</button>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-6 py-20">
        <div className="max-w-4xl mx-auto">
          {activeTab === "login" && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <div className="mb-8 text-center">
                <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">{isLogin ? "Welcome Back" : "Create Account"}</h1>
                <p className="text-slate-400">{isLogin ? "Sign in to access your certificates." : "Register to start receiving verifiable credentials."}</p>
              </div>
              <Card className="bg-slate-900 border-slate-800 max-w-md mx-auto">
                <CardHeader>
                  <CardTitle>{isLogin ? "Login" : "Sign Up"}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm text-slate-400">Name</label>
                    <input type="text" value={authData.name} onChange={e => setAuthData({ ...authData, name: e.target.value })} className="w-full bg-slate-950 border-slate-800 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  {!isLogin && (
                    <div className="space-y-2">
                      <label className="text-sm text-slate-400">Email</label>
                      <input type="email" value={authData.email} onChange={e => setAuthData({ ...authData, email: e.target.value })} className="w-full bg-slate-950 border-slate-800 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-indigo-500" />
                    </div>
                  )}
                  <div className="space-y-2">
                    <label className="text-sm text-slate-400">Password</label>
                    <input type="password" value={authData.password} onChange={e => setAuthData({ ...authData, password: e.target.value })} className="w-full bg-slate-950 border-slate-800 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  {uploadStatus && <p className="text-sm text-red-400">{uploadStatus}</p>}
                </CardContent>
                <CardFooter className="flex flex-col gap-4">
                  <Button onClick={handleAuth} className="w-full bg-indigo-600 hover:bg-indigo-700">{isLogin ? "Login" : "Sign Up"}</Button>
                  <button onClick={() => { setIsLogin(!isLogin); setUploadStatus(""); }} className="text-sm text-indigo-400 hover:underline">
                    {isLogin ? "Need an account? Sign up" : "Already have an account? Login"}
                  </button>
                </CardFooter>
              </Card>
            </motion.div>
          )}

          {activeTab === "admin" && user?.is_admin && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <div className="mb-8 text-center">
                <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">Issue Certificates</h1>
                <p className="text-slate-400">Upload CSV data to bulk issue verifiable blockchain-ready credentials.</p>
              </div>

              <Card className="bg-slate-900 border-slate-800">
                <CardHeader>
                  <CardTitle>Bulk Import</CardTitle>
                  <CardDescription>Select a CSV file containing 'student_name' and 'course_name'.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="border-2 border-dashed border-slate-800 rounded-xl p-10 flex flex-col items-center justify-center gap-4 hover:border-indigo-500/50 transition-colors bg-slate-950/50">
                    <Upload className="w-10 h-10 text-slate-600" />
                    <input type="file" accept=".csv" onChange={handleFileChange} className="text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-500/10 file:text-indigo-400 hover:file:bg-indigo-500/20" />
                  </div>
                  {uploadStatus && <p className="mt-4 text-sm text-center text-emerald-400">{uploadStatus}</p>}
                </CardContent>
                <CardFooter>
                  <Button onClick={handleImport} disabled={!file} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">Import & Issue</Button>
                </CardFooter>
              </Card>
            </motion.div>
          )}

          {activeTab === "student" && user && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <div className="mb-8 text-center">
                <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">My Credentials</h1>
                <p className="text-slate-400">Welcome, {user.name}! Here are your verified certificates.</p>
              </div>

              <div className="flex gap-4 mb-8 justify-center">
                <Button onClick={() => {
                  const fetchCertificates = async () => {
                    try {
                      const res = await axios.get(`http://localhost:8000/api/certificates/${user.name}`)
                      setCertificates(res.data)
                    } catch (error) {
                      console.error(error)
                    }
                  }
                  fetchCertificates();
                }} variant="secondary" className="flex items-center gap-2">
                  <Search className="w-4 h-4" /> Refresh List
                </Button>
              </div>

              <div className="grid gap-4">
                {certificates.map((cert) => (
                  <Card key={cert.id} className="bg-slate-900 border-slate-800">
                    <CardHeader className="flex flex-row items-center justify-between">
                      <div>
                        <CardTitle className="text-lg">{cert.course_name}</CardTitle>
                        <CardDescription>Issued to {cert.student_name} on {new Date(cert.issued_at).toLocaleDateString()}</CardDescription>
                      </div>
                      <CheckCircle className="text-emerald-500 w-6 h-6" />
                    </CardHeader>
                    <CardFooter className="gap-2">
                      <Button variant="outline" size="sm" onClick={() => window.location.href = `http://localhost:8000/api/download/${cert.id}`}>
                        <Download className="w-4 h-4 mr-2" /> Download PDF
                      </Button>
                      <span className="text-xs text-slate-600 font-mono ml-auto">ID: {cert.id}</span>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === "verifier" && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <div className="mb-8 text-center">
                <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">Verify Credential</h1>
                <p className="text-slate-400">Instantly verify the authenticity of a certificate.</p>
              </div>

              <Card className="bg-slate-900 border-slate-800">
                <CardContent className="pt-6">
                  <div className="flex gap-4 mb-6">
                    <input
                      type="text"
                      placeholder="Paste Certificate ID"
                      value={verifyId}
                      onChange={(e) => setVerifyId(e.target.value)}
                      className="flex-1 bg-slate-950 border-slate-800 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-amber-500/50 text-white placeholder:text-slate-600 font-mono text-sm"
                    />
                    <Button onClick={handleVerify} className="bg-amber-600 hover:bg-amber-700 text-white">Verify</Button>
                  </div>

                  {verifyResult && (
                    <div className={`p-6 rounded-xl border ${verifyResult.valid ? "bg-emerald-500/10 border-emerald-500/20" : "bg-red-500/10 border-red-500/20"}`}>
                      <div className="flex items-center gap-3 mb-2">
                        {verifyResult.valid ? <CheckCircle className="text-emerald-500" /> : <Shield className="text-red-500" />}
                        <h3 className={`font-bold ${verifyResult.valid ? "text-emerald-400" : "text-red-400"}`}>
                          {verifyResult.valid ? "Valid Certificate" : "Invalid Certificate"}
                        </h3>
                      </div>
                      {verifyResult.valid && (
                        <div className="text-sm text-slate-400 pl-9">
                          <p>Student: <span className="text-slate-200">{verifyResult.certificate.student_name}</span></p>
                          <p>Course: <span className="text-slate-200">{verifyResult.certificate.course_name}</span></p>
                          <p>Issuer Signature: <span className="text-slate-200 font-mono text-xs">{verifyResult.certificate.signature.substring(0, 20)}...</span></p>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}
