import { BrowserRouter, Routes, Route } from "react-router-dom";

import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Forgotpassword from "./pages/Forgotpassword";
import Completeprofile from "./pages/Completeprofile";

import Profile from "./pages/Profile";
import Aiassistant from "./pages/Aiassistant"

function App() {
  return (
    
      <Routes>

       
        <Route path="/" element={<Welcome />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<Forgotpassword />} />
        <Route path="/complete-profile" element={<Completeprofile />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/ai-assistant" element={<Aiassistant/>} />

      </Routes>
  
  );
}

export default App;