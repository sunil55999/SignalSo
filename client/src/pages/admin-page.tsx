import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { insertChannelSchema, insertUserSchema, type Channel, type User } from "@shared/schema";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { z } from "zod";

const channelFormSchema = insertChannelSchema.extend({
  name: z.string().min(1, "Channel name is required"),
});

const userFormSchema = insertUserSchema.extend({
  username: z.string().min(3, "Username must be at least 3 characters"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type ChannelForm = z.infer<typeof channelFormSchema>;
type UserForm = z.infer<typeof userFormSchema>;

export default function AdminPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("channels");
  const [isChannelModalOpen, setIsChannelModalOpen] = useState(false);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);

  // Fetch channels
  const { data: channels, isLoading: channelsLoading } = useQuery({
    queryKey: ["/api/channels"],
    refetchInterval: 30000,
  });

  // Fetch sync logs
  const { data: syncLogs, isLoading: logsLoading } = useQuery({
    queryKey: ["/api/sync-logs"],
    refetchInterval: 10000,
  });

  // Channel form
  const channelForm = useForm<ChannelForm>({
    resolver: zodResolver(channelFormSchema),
    defaultValues: {
      name: "",
      telegramId: "",
      description: "",
      isActive: true,
    },
  });

  // User form
  const userForm = useForm<UserForm>({
    resolver: zodResolver(userFormSchema),
    defaultValues: {
      username: "",
      password: "",
      email: "",
      role: "user",
    },
  });

  // Channel mutations
  const createChannelMutation = useMutation({
    mutationFn: async (data: ChannelForm) => {
      const res = await apiRequest("POST", "/api/channels", data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/channels"] });
      setIsChannelModalOpen(false);
      channelForm.reset();
      toast({
        title: "Channel created",
        description: "Channel has been successfully created",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const updateChannelMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<ChannelForm> }) => {
      const res = await apiRequest("PUT", `/api/channels/${id}`, data);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/channels"] });
      setEditingChannel(null);
      setIsChannelModalOpen(false);
      channelForm.reset();
      toast({
        title: "Channel updated",
        description: "Channel has been successfully updated",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const deleteChannelMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiRequest("DELETE", `/api/channels/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/channels"] });
      toast({
        title: "Channel deleted",
        description: "Channel has been successfully deleted",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const onChannelSubmit = (data: ChannelForm) => {
    if (editingChannel) {
      updateChannelMutation.mutate({ id: editingChannel.id, data });
    } else {
      createChannelMutation.mutate(data);
    }
  };

  const handleEditChannel = (channel: Channel) => {
    setEditingChannel(channel);
    channelForm.reset({
      name: channel.name,
      telegramId: channel.telegramId || "",
      description: channel.description || "",
      isActive: channel.isActive,
    });
    setIsChannelModalOpen(true);
  };

  const handleDeleteChannel = async (id: number) => {
    if (confirm("Are you sure you want to delete this channel?")) {
      deleteChannelMutation.mutate(id);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-dark">Admin Panel</h1>
        <p className="text-muted mt-2">Manage users, channels, and system configuration</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="logs">Sync Logs</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="channels" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Channel Management</CardTitle>
              <Dialog open={isChannelModalOpen} onOpenChange={setIsChannelModalOpen}>
                <DialogTrigger asChild>
                  <Button onClick={() => {
                    setEditingChannel(null);
                    channelForm.reset({
                      name: "",
                      telegramId: "",
                      description: "",
                      isActive: true,
                    });
                  }}>
                    <i className="fas fa-plus mr-2"></i>
                    Add Channel
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>
                      {editingChannel ? "Edit Channel" : "Create New Channel"}
                    </DialogTitle>
                  </DialogHeader>
                  <Form {...channelForm}>
                    <form onSubmit={channelForm.handleSubmit(onChannelSubmit)} className="space-y-4">
                      <FormField
                        control={channelForm.control}
                        name="name"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Channel Name</FormLabel>
                            <FormControl>
                              <Input placeholder="Enter channel name" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={channelForm.control}
                        name="telegramId"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Telegram ID</FormLabel>
                            <FormControl>
                              <Input placeholder="Enter Telegram channel ID" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={channelForm.control}
                        name="description"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Description</FormLabel>
                            <FormControl>
                              <Input placeholder="Enter channel description" {...field} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <div className="flex justify-end space-x-2">
                        <Button 
                          type="button" 
                          variant="outline" 
                          onClick={() => setIsChannelModalOpen(false)}
                        >
                          Cancel
                        </Button>
                        <Button 
                          type="submit" 
                          disabled={createChannelMutation.isPending || updateChannelMutation.isPending}
                        >
                          {editingChannel ? "Update" : "Create"} Channel
                        </Button>
                      </div>
                    </form>
                  </Form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {channelsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <i className="fas fa-spinner fa-spin text-2xl text-muted"></i>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Telegram ID</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {channels?.map((channel: Channel) => (
                      <TableRow key={channel.id}>
                        <TableCell className="font-medium">{channel.name}</TableCell>
                        <TableCell>{channel.telegramId || "—"}</TableCell>
                        <TableCell>
                          <Badge variant={channel.isActive ? "default" : "secondary"}>
                            {channel.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {channel.createdAt ? new Date(channel.createdAt).toLocaleDateString() : "—"}
                        </TableCell>
                        <TableCell>
                          <div className="flex space-x-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditChannel(channel)}
                            >
                              <i className="fas fa-edit"></i>
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteChannel(channel.id)}
                              className="text-destructive hover:text-destructive"
                            >
                              <i className="fas fa-trash"></i>
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="users" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <i className="fas fa-users text-4xl text-gray-400 mb-4"></i>
                <p className="text-gray-500 font-medium">User Management Interface</p>
                <p className="text-sm text-gray-400">Create and manage user accounts</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Sync Logs</CardTitle>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <i className="fas fa-spinner fa-spin text-2xl text-muted"></i>
                </div>
              ) : (
                <div className="space-y-4">
                  {syncLogs?.map((log: any) => (
                    <div key={log.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <p className="font-medium">{log.action}</p>
                        <p className="text-sm text-muted">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : "—"}
                        </p>
                      </div>
                      <Badge variant={log.status === "success" ? "default" : "destructive"}>
                        {log.status}
                      </Badge>
                    </div>
                  )) || (
                    <div className="text-center py-8">
                      <i className="fas fa-file-alt text-4xl text-gray-400 mb-4"></i>
                      <p className="text-gray-500">No sync logs available</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>System Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Server Status</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>API Status:</span>
                      <Badge variant="default">Online</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span>Database:</span>
                      <Badge variant="default">Connected</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span>WebSocket:</span>
                      <Badge variant="default">Active</Badge>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Configuration</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Signal Parser:</span>
                      <span className="text-sm text-muted">v2.0.0</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Retry Engine:</span>
                      <span className="text-sm text-muted">Enabled</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Sync Interval:</span>
                      <span className="text-sm text-muted">60s</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}