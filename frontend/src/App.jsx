import { BrowserRouter, Routes, Route } from "react-router-dom";

import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Forgotpassword from "./pages/Forgotpassword";
import Resetpassword from "./pages/Resetpassword";
import Completeprofile from "./pages/Completeprofile";
import ProtectedRoute from "./components/ProtectedRoute";

import Aiassistant from "./pages/Aiassistant"

function App() {
  return (

      <Routes>


        <Route path="/" element={<Welcome />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<Forgotpassword />} />
        <Route path="/reset-password" element={<Resetpassword />} />
        <Route path="/complete-profile" element={<ProtectedRoute><Completeprofile /></ProtectedRoute>} />
        <Route path="/ai-assistant" element={<ProtectedRoute><Aiassistant /></ProtectedRoute>} />

      </Routes>
  
  );
}

export default App;