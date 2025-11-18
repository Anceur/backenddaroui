"""
Views for IngredientStock and IngredientTrace management
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin
from .models import IngredientStock, IngredientTrace, Ingredient
from .serializers import IngredientStockSerializer, IngredientTraceSerializer
from django.db.models import Q


class IngredientStockListCreateView(APIView):
    """View for listing all ingredient stocks and creating new stock records"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all ingredient stocks"""
        try:
            stocks = IngredientStock.objects.select_related('ingredient').all().order_by('ingredient__name')
            serializer = IngredientStockSerializer(stocks, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve ingredient stocks',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new ingredient stock record"""
        try:
            serializer = IngredientStockSerializer(data=request.data)
            if serializer.is_valid():
                stock = serializer.save()
                # Also update the Ingredient model's stock field
                stock.ingredient.stock = stock.quantity
                stock.ingredient.save(update_fields=['stock'])
                return Response(
                    IngredientStockSerializer(stock).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create ingredient stock',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IngredientStockDetailView(APIView):
    """View for retrieving, updating, or deleting a specific ingredient stock"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, stock_id):
        """Get a specific ingredient stock by ID"""
        try:
            stock = IngredientStock.objects.select_related('ingredient').get(id=stock_id)
            serializer = IngredientStockSerializer(stock)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except IngredientStock.DoesNotExist:
            return Response({
                'error': 'Ingredient stock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve ingredient stock',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, stock_id):
        """Full update of an ingredient stock"""
        try:
            stock = IngredientStock.objects.get(id=stock_id)
            serializer = IngredientStockSerializer(stock, data=request.data)
            if serializer.is_valid():
                stock = serializer.save()
                # Also update the Ingredient model's stock field
                stock.ingredient.stock = stock.quantity
                stock.ingredient.save(update_fields=['stock'])
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except IngredientStock.DoesNotExist:
            return Response({
                'error': 'Ingredient stock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update ingredient stock',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, stock_id):
        """Partial update of an ingredient stock"""
        try:
            stock = IngredientStock.objects.get(id=stock_id)
            serializer = IngredientStockSerializer(stock, data=request.data, partial=True)
            if serializer.is_valid():
                stock = serializer.save()
                # Also update the Ingredient model's stock field
                stock.ingredient.stock = stock.quantity
                stock.ingredient.save(update_fields=['stock'])
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except IngredientStock.DoesNotExist:
            return Response({
                'error': 'Ingredient stock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update ingredient stock',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, stock_id):
        """Delete an ingredient stock record"""
        try:
            stock = IngredientStock.objects.get(id=stock_id)
            stock.delete()
            return Response({
                'message': 'Ingredient stock deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except IngredientStock.DoesNotExist:
            return Response({
                'error': 'Ingredient stock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete ingredient stock',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IngredientTraceListView(APIView):
    """View for listing ingredient traces (admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all ingredient traces with optional filtering"""
        try:
            traces = IngredientTrace.objects.select_related(
                'ingredient', 'order', 'used_by'
            ).all().order_by('-timestamp')
            
            # Optional filters
            ingredient_id = request.query_params.get('ingredient', None)
            order_id = request.query_params.get('order', None)
            
            if ingredient_id:
                try:
                    traces = traces.filter(ingredient_id=int(ingredient_id))
                except ValueError:
                    pass
            
            if order_id:
                try:
                    # Remove '#' if present
                    order_id_clean = str(order_id).replace('#', '')
                    traces = traces.filter(order_id=int(order_id_clean))
                except ValueError:
                    pass
            
            # Pagination
            try:
                page = int(request.query_params.get('page', 1))
                if page < 1:
                    page = 1
            except (ValueError, TypeError):
                page = 1
            
            try:
                page_size = int(request.query_params.get('page_size', 50))
                if page_size < 1:
                    page_size = 50
            except (ValueError, TypeError):
                page_size = 50
            
            total_count = traces.count()
            total_pages = (total_count + page_size - 1) // page_size
            
            start = (page - 1) * page_size
            end = start + page_size
            paginated_traces = traces[start:end]
            
            serializer = IngredientTraceSerializer(paginated_traces, many=True)
            
            return Response({
                'traces': serializer.data,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve ingredient traces',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IngredientTraceDetailView(APIView):
    """View for retrieving a specific ingredient trace (admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, trace_id):
        """Get a specific ingredient trace by ID"""
        try:
            trace = IngredientTrace.objects.select_related(
                'ingredient', 'order', 'used_by'
            ).get(id=trace_id)
            serializer = IngredientTraceSerializer(trace)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except IngredientTrace.DoesNotExist:
            return Response({
                'error': 'Ingredient trace not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve ingredient trace',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

