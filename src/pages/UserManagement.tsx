import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { 
  Users, 
  UserPlus,
  Truck,
  BarChart3,
  RefreshCw,
  Edit,
  Trash2,
  Plus,
  Search,
  Filter,
  Crown,
  Briefcase,
  User,
  Shield,
  Activity,
  Target,
  Clock
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { env } from "@/lib/env";

// Types
interface TransportMethod {
  id: number;
  name: string;
  name_fa: string;
  description?: string;
  is_active: boolean;
  created_at: string;
}

interface User {
  id: number;
  username: string;
  full_name: string;
  email?: string;
  phone?: string;
  role: string;
  department?: string;
  is_active: boolean;
  can_handle_domestic: boolean;
  can_handle_international: boolean;
  created_at: string;
  last_login_at?: string;
  manager?: {
    id: number;
    name: string;
  };
  subordinates_count: number;
  specializations: {
    id: number;
    transport_method: {
      id: number;
      name: string;
    };
    proficiency_level: string;
    is_primary: boolean;
  }[];
  workload: number;
}

interface AssignmentRule {
  id: number;
  name: string;
  description?: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  priority: number;
  is_active: boolean;
  created_by: {
    id: number;
    name: string;
  };
  created_at: string;
  updated_at: string;
}

interface AssignmentStatistics {
  total_assignments: number;
  automatic_assignments: number;
  manual_assignments: number;
  expert_workloads: {
    expert_id: number;
    expert_name: string;
    workload: number;
  }[];
}

const UserManagement = () => {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [transportMethods, setTransportMethods] = useState<TransportMethod[]>([]);
  const [assignmentRules, setAssignmentRules] = useState<AssignmentRule[]>([]);
  const [statistics, setStatistics] = useState<AssignmentStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("users");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRole, setSelectedRole] = useState("all");
  
  // Dialog states
  const [userDialogOpen, setUserDialogOpen] = useState(false);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [transportDialogOpen, setTransportDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editingRule, setEditingRule] = useState<AssignmentRule | null>(null);
  
  // User form states
  const [userFormData, setUserFormData] = useState({
    username: "",
    password: "",
    full_name: "",
    email: "",
    phone: "",
    role: "expert",
    department: "",
    is_active: true,
    can_handle_domestic: true,
    can_handle_international: true
  });
  const [creatingUser, setCreatingUser] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editFormData, setEditFormData] = useState({
    full_name: "",
    phone: "",
    username: "",
    password: "",
    is_active: true,
    can_handle_domestic: true,
    can_handle_international: true
  });
  const [updatingUser, setUpdatingUser] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);
  const [deletingUser, setDeletingUser] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('expert_token');
      const [usersRes, transportRes, rulesRes, statsRes] = await Promise.all([
        fetch(`${env.API_URL}/api/user-management/users`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        }),
        fetch(`${env.API_URL}/api/user-management/transport-methods`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        }),
        fetch(`${env.API_URL}/api/user-management/assignment-rules`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        }),
        fetch(`${env.API_URL}/api/user-management/assignment-statistics`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        })
      ]);

      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData.users);
      }

      if (transportRes.ok) {
        const transportData = await transportRes.json();
        setTransportMethods(transportData.transport_methods);
      }

      if (rulesRes.ok) {
        const rulesData = await rulesRes.json();
        setAssignmentRules(rulesData.assignment_rules);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStatistics(statsData);
      }
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در بارگذاری داده‌ها",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "admin": return <Shield className="w-4 h-4" />;
      case "crm_manager": return <Crown className="w-4 h-4" />;
      case "business_expert": return <Briefcase className="w-4 h-4" />;
      case "expert": return <User className="w-4 h-4" />;
      default: return <User className="w-4 h-4" />;
    }
  };

  const getRoleLabel = (role: string) => {
    const labels: Record<string, string> = {
      admin: "مدیر سیستم",
      crm_manager: "مدیر CRM",
      business_expert: "کارشناس بازرگانی",
      expert: "کارشناس",
      supervisor: "سرپرست"
    };
    return labels[role] || role;
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case "admin": return "bg-red-100 text-red-800";
      case "crm_manager": return "bg-purple-100 text-purple-800";
      case "business_expert": return "bg-blue-100 text-blue-800";
      case "expert": return "bg-green-100 text-green-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const isExpertRole = (role: string) => role === "expert" || role === "business_expert";

  const getScopeLabel = (user: User) => {
    if (user.can_handle_domestic && user.can_handle_international) return "هیبرید";
    if (user.can_handle_domestic) return "داخلی";
    if (user.can_handle_international) return "بین‌المللی";
    return "بدون حوزه";
  };

  const getProficiencyColor = (level: string) => {
    switch (level) {
      case "expert": return "bg-red-100 text-red-800";
      case "advanced": return "bg-orange-100 text-orange-800";
      case "intermediate": return "bg-yellow-100 text-yellow-800";
      case "beginner": return "bg-green-100 text-green-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getProficiencyLabel = (level: string) => {
    const labels: Record<string, string> = {
      expert: "متخصص",
      advanced: "پیشرفته",
      intermediate: "متوسط",
      beginner: "مبتدی"
    };
    return labels[level] || level;
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (user.email && user.email.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesRole = selectedRole === "all" || user.role === selectedRole;
    return matchesSearch && matchesRole;
  });

  const openEditDialog = (user: User) => {
    setEditingUser(user);
    setEditFormData({
      full_name: user.full_name,
      phone: user.phone || "",
      username: user.username,
      password: "",
      is_active: user.is_active,
      can_handle_domestic: user.can_handle_domestic,
      can_handle_international: user.can_handle_international
    });
    setEditDialogOpen(true);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setUpdatingUser(true);
    try {
      const body: Record<string, unknown> = {
        full_name: editFormData.full_name,
        phone: editFormData.phone,
        username: editFormData.username,
        is_active: editFormData.is_active,
        can_handle_domestic: editFormData.can_handle_domestic,
        can_handle_international: editFormData.can_handle_international
      };
      if (editFormData.password.trim()) {
        body.password = editFormData.password;
      }
      const token = localStorage.getItem('expert_token');
      const response = await fetch(`${env.API_URL}/api/user-management/users/${editingUser.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      if (response.ok) {
        toast({ title: "موفق", description: data.message || "کاربر به‌روزرسانی شد" });
        setEditDialogOpen(false);
        setEditingUser(null);
        loadData();
      } else {
        toast({ title: "خطا", description: data.error || "خطا در به‌روزرسانی", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "خطا", description: "خطا در ارتباط با سرور", variant: "destructive" });
    } finally {
      setUpdatingUser(false);
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      const token = localStorage.getItem('expert_token');
      const response = await fetch(`${env.API_URL}/api/user-management/users/${user.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ is_active: !user.is_active })
      });
      const data = await response.json();
      if (response.ok) {
        toast({ title: "موفق", description: data.message || "وضعیت به‌روزرسانی شد" });
        loadData();
      } else {
        toast({ title: "خطا", description: data.error || "خطا در به‌روزرسانی", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "خطا", description: "خطا در ارتباط با سرور", variant: "destructive" });
    }
  };

  const openDeleteDialog = (user: User) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    setDeletingUser(true);
    try {
      const token = localStorage.getItem('expert_token');
      const response = await fetch(`${env.API_URL}/api/user-management/users/${userToDelete.id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await response.json();
      if (response.ok) {
        toast({
          title: "موفق",
          description: data.message || "کاربر با موفقیت حذف شد"
        });
        setDeleteDialogOpen(false);
        setUserToDelete(null);
        loadData();
      } else {
        toast({
          title: "خطا",
          description: "خطا در حذف کاربر",
          variant: "destructive"
        });
      }
    } catch (error) {
      toast({
        title: "خطا",
        description: "خطا در ارتباط با سرور",
        variant: "destructive"
      });
    } finally {
      setDeletingUser(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingUser(true);

    try {
      const token = localStorage.getItem('expert_token');
      // Omit empty optional strings so backend stores None and UNIQUE on email is not violated.
      const payload: Record<string, unknown> = {
        username: userFormData.username,
        password: userFormData.password,
        full_name: userFormData.full_name,
        role: userFormData.role,
        is_active: userFormData.is_active,
        can_handle_domestic: userFormData.can_handle_domestic,
        can_handle_international: userFormData.can_handle_international,
      };
      if (userFormData.email.trim() !== "") payload.email = userFormData.email.trim();
      if (userFormData.phone.trim() !== "") payload.phone = userFormData.phone.trim();
      if (userFormData.department.trim() !== "") payload.department = userFormData.department.trim();

      const response = await fetch(`${env.API_URL}/api/user-management/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json().catch(() => null);

      if (response.ok) {
        toast({
          title: "موفق",
          description: (data && (data as { message?: string }).message) || "کاربر با موفقیت ایجاد شد"
        });
        setUserDialogOpen(false);
        setUserFormData({
          username: "",
          password: "",
          full_name: "",
          email: "",
          phone: "",
          role: "expert",
          department: "",
          is_active: true,
          can_handle_domestic: true,
          can_handle_international: true
        });
        loadData();
      } else {
        const errPayload = data as { error?: string } | null;
        let description: string;
        if (response.status === 401 || response.status === 403) {
          description = "دسترسی ندارید یا نشست شما منقضی شده است. دوباره وارد شوید.";
        } else {
          description = errPayload?.error ?? `خطا در ایجاد کاربر (کد: ${response.status})`;
        }
        if (!data && import.meta.env.DEV) {
          const text = await response.text().catch(() => "");
          console.warn("Create user error:", response.status, text);
        }
        toast({
          title: "خطا",
          description,
          variant: "destructive"
        });
      }
    } catch (error) {
      if (import.meta.env.DEV) console.warn("Create user request failed:", error);
      toast({
        title: "خطا",
        description: "خطا در ارتباط با سرور",
        variant: "destructive"
      });
    } finally {
      setCreatingUser(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">مدیریت کاربران</h1>
            <p className="text-gray-600 mt-1">مدیریت سلسله مراتبی کاربران</p>
          </div>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={loadData}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ml-2 ${loading ? "animate-spin" : ""}`} />
              به‌روزرسانی
            </Button>
            <Button size="sm" onClick={() => setUserDialogOpen(true)}>
              <UserPlus className="w-4 h-4 ml-2" />
              کاربر جدید
            </Button>
          </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">کل ارجاعات</p>
                    <p className="text-3xl font-bold text-blue-600">{statistics.total_assignments}</p>
                  </div>
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Activity className="w-8 h-8 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">ارجاعات خودکار</p>
                    <p className="text-3xl font-bold text-green-600">{statistics.automatic_assignments}</p>
                  </div>
                  <div className="p-3 bg-green-100 rounded-lg">
                    <Target className="w-8 h-8 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">ارجاعات دستی</p>
                    <p className="text-3xl font-bold text-orange-600">{statistics.manual_assignments}</p>
                  </div>
                  <div className="p-3 bg-orange-100 rounded-lg">
                    <Users className="w-8 h-8 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">کارشناسان فعال</p>
                    <p className="text-3xl font-bold text-purple-600">{statistics.expert_workloads.length}</p>
                  </div>
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Briefcase className="w-8 h-8 text-purple-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Main Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="users">
              <Users className="w-4 h-4 ml-2" />
              کاربران
            </TabsTrigger>
            <TabsTrigger value="transport">
              <Truck className="w-4 h-4 ml-2" />
              روش‌های حمل
            </TabsTrigger>
            <TabsTrigger value="statistics">
              <BarChart3 className="w-4 h-4 ml-2" />
              آمار و گزارش
            </TabsTrigger>
          </TabsList>

          <TabsContent value="users" className="space-y-4">
            {/* Users Filters */}
            <Card>
              <CardContent className="p-4">
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1">
                    <div className="relative">
                      <Search className="absolute right-3 top-3 w-4 h-4 text-gray-400" />
                      <Input
                        placeholder="جستجو در کاربران..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pr-10"
                      />
                    </div>
                  </div>
                  <Select value={selectedRole} onValueChange={setSelectedRole}>
                    <SelectTrigger className="w-full md:w-48">
                      <SelectValue placeholder="نقش کاربر" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">همه نقش‌ها</SelectItem>
                      <SelectItem value="admin">مدیر سیستم</SelectItem>
                      <SelectItem value="crm_manager">مدیر CRM</SelectItem>
                      <SelectItem value="business_expert">کارشناس بازرگانی</SelectItem>
                      <SelectItem value="expert">کارشناس</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Users List */}
            {loading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
              </div>
            ) : filteredUsers.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">کاربری یافت نشد</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {filteredUsers.map((user) => (
                  <Card key={user.id}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-3">
                            {getRoleIcon(user.role)}
                            <h3 className="font-semibold text-lg">{user.full_name}</h3>
                            <Badge className={getRoleColor(user.role)}>
                              {getRoleLabel(user.role)}
                            </Badge>
                            {isExpertRole(user.role) && (
                              <Badge variant="secondary">{getScopeLabel(user)}</Badge>
                            )}
                            {!user.is_active && (
                              <Badge variant="outline" className="text-red-600">
                                غیرفعال
                              </Badge>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            <span>@{user.username}</span>
                            {user.email && (
                              <span>{user.email}</span>
                            )}
                            {user.phone && (
                              <span>{user.phone}</span>
                            )}
                            {user.department && (
                              <span>بخش: {user.department}</span>
                            )}
                          </div>

                          {user.manager && (
                            <div className="text-sm text-gray-600">
                              <span className="font-medium">مدیر:</span> {user.manager.name}
                            </div>
                          )}

                          {user.subordinates_count > 0 && (
                            <div className="text-sm text-gray-600">
                              <span className="font-medium">زیردستان:</span> {user.subordinates_count} نفر
                            </div>
                          )}

                          <div className="flex items-center gap-4 text-sm text-gray-500">
                            <span>بار کاری: {user.workload}</span>
                            <span>•</span>
                            <span>تخصص‌ها: {user.specializations.length}</span>
                            {user.last_login_at && (
                              <>
                                <span>•</span>
                                <span>
                                  آخرین ورود: {new Date(user.last_login_at).toLocaleDateString("fa-IR")}
                                </span>
                              </>
                            )}
                          </div>

                          {/* Specializations */}
                          {user.specializations.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                              {user.specializations.map((spec) => (
                                <Badge key={spec.id} variant="outline" className="text-xs">
                                  {spec.transport_method.name}
                                  {spec.is_primary && " (اصلی)"}
                                  <span className="mr-1">-</span>
                                  <span className={getProficiencyColor(spec.proficiency_level)}>
                                    {getProficiencyLabel(spec.proficiency_level)}
                                  </span>
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>

                        <div className="flex gap-2 items-center">
                          {user.role !== "admin" && user.role !== "expert" && (
                            <Button
                              size="sm"
                              variant={user.is_active ? "outline" : "secondary"}
                              onClick={() => handleToggleActive(user)}
                            >
                              {user.is_active ? "غیرفعال کردن" : "فعال کردن"}
                            </Button>
                          )}
                          <Button size="sm" variant="outline" onClick={() => openEditDialog(user)}>
                            <Edit className="w-4 h-4 ml-2" />
                            ویرایش
                          </Button>
                          {user.role !== "admin" && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => openDeleteDialog(user)}
                            >
                              <Trash2 className="w-4 h-4 ml-2" />
                              حذف
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="transport" className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">روش‌های حمل و نقل</h3>
              <Button size="sm" onClick={() => setTransportDialogOpen(true)}>
                <Plus className="w-4 h-4 ml-2" />
                روش جدید
              </Button>
            </div>

            <div className="grid gap-4">
              {transportMethods.map((method) => (
                <Card key={method.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium">{method.name_fa}</h4>
                        <p className="text-sm text-gray-600">{method.name}</p>
                        {method.description && (
                          <p className="text-sm text-gray-500 mt-1">{method.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={method.is_active ? "default" : "secondary"}>
                          {method.is_active ? "فعال" : "غیرفعال"}
                        </Badge>
                        <Button size="sm" variant="outline">
                          <Edit className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="statistics" className="space-y-4">
            <h3 className="text-lg font-semibold">آمار و گزارش‌ها</h3>
            
            {statistics && (
              <div className="grid gap-6">
                {/* Expert Workloads */}
                <Card>
                  <CardHeader>
                    <CardTitle>بار کاری کارشناسان</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {statistics.expert_workloads.map((expert) => (
                        <div key={expert.expert_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <p className="font-medium">{expert.expert_name}</p>
                            <p className="text-sm text-gray-600">ID: {expert.expert_id}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={expert.workload > 5 ? "destructive" : expert.workload > 3 ? "default" : "secondary"}>
                              {expert.workload} درخواست
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* Create User Dialog */}
      <Dialog open={userDialogOpen} onOpenChange={setUserDialogOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>ایجاد کاربر جدید</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateUser} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="username">نام کاربری *</Label>
                <Input
                  id="username"
                  value={userFormData.username}
                  onChange={(e) => setUserFormData({ ...userFormData, username: e.target.value })}
                  placeholder="نام کاربری"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">رمز عبور *</Label>
                <Input
                  id="password"
                  type="password"
                  value={userFormData.password}
                  onChange={(e) => setUserFormData({ ...userFormData, password: e.target.value })}
                  placeholder="رمز عبور"
                  required
                  minLength={6}
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                {isExpertRole(userFormData.role) && (
                  <fieldset className="rounded-md border p-3">
                    <legend className="px-1 text-sm font-medium">حوزه فعالیت کارشناس</legend>
                    <div className="mt-2 flex flex-wrap gap-5">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={userFormData.can_handle_domestic}
                          onChange={(e) => setUserFormData({ ...userFormData, can_handle_domestic: e.target.checked })} />
                        حمل داخلی
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={userFormData.can_handle_international}
                          onChange={(e) => setUserFormData({ ...userFormData, can_handle_international: e.target.checked })} />
                        حمل بین‌المللی
                      </label>
                    </div>
                  </fieldset>
                )}
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="full_name">نام کامل *</Label>
                <Input
                  id="full_name"
                  value={userFormData.full_name}
                  onChange={(e) => setUserFormData({ ...userFormData, full_name: e.target.value })}
                  placeholder="نام و نام خانوادگی"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">ایمیل</Label>
                <Input
                  id="email"
                  type="email"
                  value={userFormData.email}
                  onChange={(e) => setUserFormData({ ...userFormData, email: e.target.value })}
                  placeholder="email@example.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">شماره تماس</Label>
                <Input
                  id="phone"
                  value={userFormData.phone}
                  onChange={(e) => setUserFormData({ ...userFormData, phone: e.target.value })}
                  placeholder="09123456789"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">نقش کاربر *</Label>
                <Select
                  value={userFormData.role}
                  onValueChange={(value) => setUserFormData({ ...userFormData, role: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="انتخاب نقش" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expert">کارشناس</SelectItem>
                    <SelectItem value="business_expert">کارشناس بازرگانی</SelectItem>
                    <SelectItem value="supervisor">سرپرست</SelectItem>
                    <SelectItem value="crm_manager">مدیر CRM</SelectItem>
                    <SelectItem value="admin">مدیر سیستم</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="department">بخش</Label>
                <Input
                  id="department"
                  value={userFormData.department}
                  onChange={(e) => setUserFormData({ ...userFormData, department: e.target.value })}
                  placeholder="بخش کاری"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <div className="flex items-center space-x-2 space-x-reverse">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={userFormData.is_active}
                    onChange={(e) => setUserFormData({ ...userFormData, is_active: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <Label htmlFor="is_active" className="cursor-pointer">
                    کاربر فعال است
                  </Label>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setUserDialogOpen(false);
                  setUserFormData({
                    username: "",
                    password: "",
                    full_name: "",
                    email: "",
                    phone: "",
                    role: "expert",
                    department: "",
                    is_active: true,
                    can_handle_domestic: true,
                    can_handle_international: true
                  });
                }}
              >
                انصراف
              </Button>
              <Button type="submit" disabled={creatingUser}>
                {creatingUser ? (
                  <>
                    <RefreshCw className="w-4 h-4 ml-2 animate-spin" />
                    در حال ایجاد...
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4 ml-2" />
                    ایجاد کاربر
                  </>
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>ویرایش کاربر</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdateUser} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit_full_name">نام و نام خانوادگی *</Label>
              <Input
                id="edit_full_name"
                value={editFormData.full_name}
                onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                placeholder="نام و نام خانوادگی"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_phone">شماره تماس</Label>
              <Input
                id="edit_phone"
                value={editFormData.phone}
                onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                placeholder="09123456789"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_username">نام کاربری *</Label>
              <Input
                id="edit_username"
                value={editFormData.username}
                onChange={(e) => setEditFormData({ ...editFormData, username: e.target.value })}
                placeholder="نام کاربری"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit_password">رمز عبور (خالی بگذارید تا تغییر نکند)</Label>
              <Input
                id="edit_password"
                type="password"
                value={editFormData.password}
                onChange={(e) => setEditFormData({ ...editFormData, password: e.target.value })}
                placeholder="رمز عبور جدید"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="edit_is_active"
                checked={editFormData.is_active}
                onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.checked })}
                className="w-4 h-4"
              />
              <Label htmlFor="edit_is_active" className="cursor-pointer">
                کاربر فعال است
              </Label>
            </div>
            {editingUser && isExpertRole(editingUser.role) && (
              <fieldset className="rounded-md border p-3">
                <legend className="px-1 text-sm font-medium">حوزه فعالیت کارشناس</legend>
                <div className="mt-2 flex flex-wrap gap-5">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={editFormData.can_handle_domestic}
                      onChange={(e) => setEditFormData({ ...editFormData, can_handle_domestic: e.target.checked })} />
                    حمل داخلی
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={editFormData.can_handle_international}
                      onChange={(e) => setEditFormData({ ...editFormData, can_handle_international: e.target.checked })} />
                    حمل بین‌المللی
                  </label>
                </div>
              </fieldset>
            )}
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={() => setEditDialogOpen(false)}>
                انصراف
              </Button>
              <Button type="submit" disabled={updatingUser}>
                {updatingUser ? (
                  <>
                    <RefreshCw className="w-4 h-4 ml-2 animate-spin" />
                    در حال ذخیره...
                  </>
                ) : (
                  "ذخیره"
                )}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete User Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>حذف کاربر</AlertDialogTitle>
            <AlertDialogDescription>
              آیا از حذف دائمی این کاربر و اطلاعات وابسته به او اطمینان دارید؟
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="gap-2 sm:gap-0">
            <AlertDialogCancel disabled={deletingUser}>انصراف</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                handleDeleteUser();
              }}
              disabled={deletingUser}
              className="bg-red-600 hover:bg-red-700"
            >
              {deletingUser ? (
                <>
                  <RefreshCw className="w-4 h-4 ml-2 animate-spin" />
                  در حال حذف...
                </>
              ) : (
                "حذف کاربر"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default UserManagement;
