import { useState, useEffect, useRef } from "react";
import { Search, Filter, X, Calendar, User, MapPin, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar as CalendarComponent } from "@/components/ui/calendar";
import { format } from "date-fns";

interface SearchFilter {
  field: string;
  operator: string;
  value: string;
}

interface AdvancedSearchProps {
  onSearch: (query: string, filters: SearchFilter[]) => void;
  onClear: () => void;
  placeholder?: string;
  searchFields?: Array<{
    key: string;
    label: string;
    type: 'text' | 'select' | 'date' | 'number';
    options?: Array<{ value: string; label: string }>;
  }>;
  className?: string;
}

const AdvancedSearch = ({
  onSearch,
  onClear,
  placeholder = "جستجو...",
  searchFields = [],
  className = ""
}: AdvancedSearchProps) => {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilter[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Default search fields if none provided
  const defaultFields = [
    { key: 'name', label: 'نام', type: 'text' as const },
    { key: 'email', label: 'ایمیل', type: 'text' as const },
    { key: 'phone', label: 'تلفن', type: 'text' as const },
    { key: 'status', label: 'وضعیت', type: 'select' as const, options: [
      { value: 'active', label: 'فعال' },
      { value: 'inactive', label: 'غیرفعال' },
      { value: 'pending', label: 'در انتظار' }
    ]},
    { key: 'created_at', label: 'تاریخ ایجاد', type: 'date' as const }
  ];

  const fields = searchFields.length > 0 ? searchFields : defaultFields;

  useEffect(() => {
    // Debounce search
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      if (query.trim() || filters.length > 0) {
        setIsSearching(true);
        onSearch(query, filters);
        setTimeout(() => setIsSearching(false), 500);
      }
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [query, filters, onSearch]);

  const addFilter = (field: string, operator: string, value: string) => {
    if (!value.trim()) return;
    
    const newFilter: SearchFilter = { field, operator, value };
    setFilters(prev => [...prev, newFilter]);
  };

  const removeFilter = (index: number) => {
    setFilters(prev => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setQuery("");
    setFilters([]);
    onClear();
  };

  const getFieldIcon = (field: string) => {
    switch (field) {
      case 'name': case 'email': case 'phone': return <User className="w-4 h-4" />;
      case 'location': case 'address': return <MapPin className="w-4 h-4" />;
      case 'cargo': case 'package': return <Package className="w-4 h-4" />;
      case 'date': case 'created_at': return <Calendar className="w-4 h-4" />;
      default: return <Search className="w-4 h-4" />;
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Main Search Bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute right-3 top-3 w-4 h-4 text-gray-400" />
          <Input
            placeholder={placeholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pr-10"
            dir="rtl"
          />
          {isSearching && (
            <div className="absolute left-3 top-3">
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
        
        <Popover open={showFilters} onOpenChange={setShowFilters}>
          <PopoverTrigger asChild>
            <Button variant="outline">
              <Filter className="w-4 h-4 ml-2" />
              فیلترها
              {filters.length > 0 && (
                <Badge variant="secondary" className="mr-2">
                  {filters.length}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80" align="end">
            <div className="space-y-4">
              <h4 className="font-medium">فیلترهای پیشرفته</h4>
              
              {fields.map((field) => (
                <div key={field.key} className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    {field.label}
                  </label>
                  
                  {field.type === 'text' && (
                    <div className="flex gap-2">
                      <Select onValueChange={(value) => addFilter(field.key, value, '')}>
                        <SelectTrigger className="w-24">
                          <SelectValue placeholder="شرط" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="contains">شامل</SelectItem>
                          <SelectItem value="equals">برابر</SelectItem>
                          <SelectItem value="starts_with">شروع با</SelectItem>
                          <SelectItem value="ends_with">پایان با</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        placeholder={`${field.label} را وارد کنید`}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const value = e.currentTarget.value;
                            if (value.trim()) {
                              addFilter(field.key, 'contains', value);
                              e.currentTarget.value = '';
                            }
                          }
                        }}
                        dir="rtl"
                      />
                    </div>
                  )}
                  
                  {field.type === 'select' && field.options && (
                    <Select onValueChange={(value) => addFilter(field.key, 'equals', value)}>
                      <SelectTrigger>
                        <SelectValue placeholder={`انتخاب ${field.label}`} />
                      </SelectTrigger>
                      <SelectContent>
                        {field.options.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  
                  {field.type === 'date' && (
                    <div className="space-y-2">
                      <CalendarComponent
                        mode="single"
                        onSelect={(date) => {
                          if (date) {
                            addFilter(field.key, 'equals', format(date, 'yyyy-MM-dd'));
                          }
                        }}
                        className="rounded-md border"
                      />
                    </div>
                  )}
                </div>
              ))}
              
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowFilters(false)}
                  className="flex-1"
                >
                  بستن
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearAll}
                  className="flex-1"
                >
                  پاک کردن همه
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        
        {(query || filters.length > 0) && (
          <Button variant="outline" onClick={clearAll}>
            <X className="w-4 h-4 ml-2" />
            پاک کردن
          </Button>
        )}
      </div>

      {/* Active Filters */}
      {filters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.map((filter, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1"
            >
              {getFieldIcon(filter.field)}
              <span className="text-xs">
                {fields.find(f => f.key === filter.field)?.label}: {filter.value}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeFilter(index)}
                className="h-4 w-4 p-0 hover:bg-transparent"
              >
                <X className="w-3 h-3" />
              </Button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdvancedSearch;
