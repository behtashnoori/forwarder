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
  Users, 
  UserPlus,
  Settings,
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
  conditions: any;
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

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [usersRes, transportRes, rulesRes, statsRes] = await Promise.all([
        fetch("/api/user-management/users", {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem('expert_token')}`
          }
        }),
        fetch("/api/user-management/transport-methods", {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem('expert_token')}`
          }
        }),
        fetch("/api/user-management/assignment-rules", {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem('expert_token')}`
          }
        }),
        fetch("/api/user-management/assignment-statistics", {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem('expert_token')}`
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

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">مدیریت کاربران</h1>
            <p className="text-gray-600 mt-1">مدیریت سلسله مراتبی کاربران و قوانین ارجاع</p>
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
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="users">
              <Users className="w-4 h-4 ml-2" />
              کاربران
            </TabsTrigger>
            <TabsTrigger value="transport">
              <Truck className="w-4 h-4 ml-2" />
              روش‌های حمل
            </TabsTrigger>
            <TabsTrigger value="rules">
              <Settings className="w-4 h-4 ml-2" />
              قوانین ارجاع
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

                        <div className="flex gap-2">
                          <Button size="sm" variant="outline">
                            <Edit className="w-4 h-4 ml-2" />
                            ویرایش
                          </Button>
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

          <TabsContent value="rules" className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">قوانین ارجاع خودکار</h3>
              <Button size="sm" onClick={() => setRuleDialogOpen(true)}>
                <Plus className="w-4 h-4 ml-2" />
                قانون جدید
              </Button>
            </div>

            <div className="grid gap-4">
              {assignmentRules.map((rule) => (
                <Card key={rule.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium">{rule.name}</h4>
                          <Badge variant={rule.is_active ? "default" : "secondary"}>
                            {rule.is_active ? "فعال" : "غیرفعال"}
                          </Badge>
                          <Badge variant="outline">
                            اولویت: {rule.priority}
                          </Badge>
                        </div>
                        {rule.description && (
                          <p className="text-sm text-gray-600 mb-2">{rule.description}</p>
                        )}
                        <div className="text-sm text-gray-500">
                          <span>نوع: {rule.rule_type}</span>
                          <span className="mr-4">•</span>
                          <span>ایجادکننده: {rule.created_by.name}</span>
                          <span className="mr-4">•</span>
                          <span>تاریخ ایجاد: {new Date(rule.created_at).toLocaleDateString("fa-IR")}</span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button size="sm" variant="outline" className="text-red-600">
                          <Trash2 className="w-4 h-4" />
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
    </div>
  );
};

export default UserManagement;
